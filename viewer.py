from pathlib import Path

import PySimpleGUI as sg
import os
from PIL import Image, ImageTk
import io
import csv

from util import Sample, Samples

"""
Simple Image Browser based on PySimpleGUI
"""

log_path = 'data/log-htr-laia-model-best.pt--03_Bullinger-test_freq.tsv'
default_img_path = str(Path('data/').absolute())

# Get the folder containing the images from the user
folder = Path(sg.popup_get_folder('Image folder to open', default_path=default_img_path))
if not folder:
    sg.popup_cancel('Cancelling')
    raise SystemExit()

# PIL supported image types
img_types = (".png", ".jpg", "jpeg", ".tiff", ".bmp")


def get_img_path(path: str, folder: Path, lower_bound: int, upper_bound: int):
    l_compraison = []
    with open(path, 'r', encoding='utf-8') as f:
        log_htr = csv.reader(f, delimiter='\t', quotechar='"', quoting=csv.QUOTE_NONE)

        for line in log_htr:
            server_path = Path('/'.join(line[0].split('/')[:-1]))
            img_name = Path(line[0]).name
            gt = line[2]
            prediction = line[1]
            diff_word = int(len(gt.split(' '))) - int(len(prediction.split(' ')))
            diff_tocken = len(gt) - len(prediction)
            new_row = Sample(server_path=server_path, img_name=img_name, gt=gt, prediction=prediction,
                             difference_token=diff_tocken, difference_word=diff_word)
            l_compraison.append(new_row)

    samples = filter(lambda e: lower_bound > e.difference_token or e.difference_token > upper_bound, l_compraison)

    res = Samples()
    for sample in samples:
        for root, dirs, files in os.walk(folder):
            if sample.img_name in files:
                sample.path = Path(root) / sample.img_name
                res.append(sample)
    return res


sample_list = get_img_path(log_path, folder, lower_bound=-5, upper_bound=5)

all_fnames = [name.img_name for name in sample_list]

num_files = len(sample_list)  # number of iamges found
if num_files == 0:
    sg.popup('No files in folder')
    raise SystemExit()


def get_img_data(file_name, maxsize=(1200, 850), first=False):
    img = Image.open(file_name)
    img.thumbnail(maxsize)
    if first:  # tkinter is inactive the first time
        bio = io.BytesIO()
        img.save(bio, format="PNG")
        del img
        return bio.getvalue()
    return ImageTk.PhotoImage(img)


# ------------------------------------------------------------------------------


# make these 2 elements outside the layout as we want to "update" them later
# initialize to the first file in the list
filename = sample_list[0].path  # name of first file in list
gt = sample_list[0].gt
image_elem = sg.Image(data=get_img_data(filename, first=True))
font = ("Arial", 25)
filename_display_elem = sg.Text(f'{sample_list[0].prediction} ; {sample_list[0].difference_token} ; {sample_list[0].img_name}', size=(80, 3), font=font)
file_num_display_elem = sg.Text('File 1 of {}'.format(num_files), size=(15, 1))
input_elem = sg.Multiline(key='new_gt', default_text=gt, size=(85, 5), font=font, expand_y=True, enter_submits=True)


# define layout, show and read the form
col = [
    [filename_display_elem],
    [image_elem],
    [input_elem]]

col_files = [[sg.Listbox(values=all_fnames, change_submits=True, size=(60, 30), key='listbox')],
             [sg.Button('Next', size=(8, 2)), sg.Button('Prev', size=(8, 2)), sg.Button('Save', size=(8, 2)), file_num_display_elem]]

layout = [[sg.Column(col_files), sg.Column(col)]]

window = sg.Window('Image Browser', layout, return_keyboard_events=True,
                   location=(0, 0), use_default_focus=False)

# loop reading the user input and displaying image, filename
i = 0
current_sample = sample_list[0]
while True:
    # read the form
    event, values = window.read()
    print(event, values)
    # perform button and keyboard operations
    if event == sg.WIN_CLOSED:
        break
    elif event in ('Next', 'MouseWheel:Down', 'Down:40', 'Next:34'):
        i += 1
        if i >= num_files:
            i -= num_files
        current_sample = sample_list[i]
        filename = current_sample.path
        values["listbox"] = filename
        current_sample.checked = True
        current_sample.corrected_gt = current_sample.gt
    elif event in ('Prev', 'MouseWheel:Up', 'Up:38', 'Prior:33'):
        i -= 1
        if i < 0:
            i = num_files + i
        current_sample = sample_list[i]
        filename = current_sample.path
    elif event == 'Save':
        save_dir = Path(sg.popup_get_folder('Image folder to open', default_path='/Users/asb/prog/soict23/data/'))
        if not save_dir:
            save_dir = folder
        save_path = save_dir / 'res.tsv'
        sample_list.save_as_tsv(save_path)
    elif event == 'listbox':  # something from the listbox
        f = values["listbox"][0]  # selected filename
        filename = f  # read this file
        current_sample = sample_list.find_by_name(f)
        i = sample_list.index(current_sample)  # update running index
    elif window["new_gt"].EnterSubmits:
        new_gt = values["new_gt"]
        window["new_gt"].update(new_gt)
        current_sample.corrected_gt = new_gt
    else:
        filename = sample_list[i].path
        gt = sample_list[i].gt

    # update window with new image
    image_elem.update(data=get_img_data(current_sample.path, first=True))
    input_elem.update(f'{current_sample.gt}') if current_sample.corrected_gt == "" else input_elem.update(
        f'{current_sample.corrected_gt}')
    # update window with filename
    filename_display_elem.update(f'{sample_list[i].prediction} ; {sample_list[i].difference_token} ; {sample_list[0].img_name}')  # filename
    # update page display
    file_num_display_elem.update('File {} of {}'.format(i + 1, num_files))

window.close()
