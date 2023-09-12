from pathlib import Path

import PySimpleGUI as sg
import os
from PIL import Image, ImageTk
import io
import csv

from util import Sample, Samples

"""
Simple Image Browser based on PySimpleGUI
--------------------------------------------
There are some improvements compared to the PNG browser of the repository:
1. Paging is cyclic, i.e. automatically wraps around if file index is outside
2. Supports all file types that are valid PIL images
3. Limits the maximum form size to the physical screen
4. When selecting an image from the listbox, subsequent paging uses its index
5. Paging performance improved significantly because of using PIL

Dependecies
------------
Python3
PIL
"""

# Get the folder containin:g the images from the user
folder = Path(sg.popup_get_folder('Image folder to open', default_path='/Users/asb/prog/soict23/data/'))
if not folder:
    sg.popup_cancel('Cancelling')
    raise SystemExit()

# PIL supported image types
img_types = (".png", ".jpg", "jpeg", ".tiff", ".bmp")

path = 'data/log-htr-laia-model-best.pt--03_Bullinger-test_freq.tsv'


# - image file
# - network output
# - ground truth
# - character edit distance
# - word edit distance
# - number of characters in the ground truth
# - ID of the GPU


def get_img_path(path: str, folder: Path, col: int, min: int, max: int):
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

    samples = filter(lambda e: min > e.difference_token or e.difference_token > max, l_compraison)

    res = Samples()
    for sample in samples:
        for root, dirs, files in os.walk(folder):
            if sample.img_name in files:
                sample.path = Path(root) / sample.img_name
                res.append(sample)
    return res


sample_list = get_img_path(path, folder, 5, -10, 10)

# create sub list of image files (no sub folders, no wrong file types)
# fnames_gt = [s for s in flist0 if s.path.is_file() and s.path.suffix in img_types]
# fnames_gt = [(f[0], f[1], f[2], f[3]) for f in flist0 if os.path.isfile(
#     f[0]) and f[0].lower().endswith(img_types)]

all_fnames = [name.img_name for name in sample_list]

num_files = len(sample_list)  # number of iamges found
if num_files == 0:
    sg.popup('No files in folder')
    raise SystemExit()


# ------------------------------------------------------------------------------
# use PIL to read data of one image
# ------------------------------------------------------------------------------


def get_img_data(f, maxsize=(1200, 850), first=False):
    """Generate image data using PIL
    """
    img = Image.open(f)
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
        input_elem.update(f'{current_sample.gt}') if current_sample.corrected_gt == "" else input_elem.update(
            f'{current_sample.corrected_gt}')
        current_sample.checked = True
        current_sample.corrected_gt = gt
    elif event in ('Prev', 'MouseWheel:Up', 'Up:38', 'Prior:33'):
        i -= 1
        if i < 0:
            i = num_files + i
        current_sample = sample_list[i]
        filename = current_sample.path
        input_elem.update(f'{current_sample.gt}') if current_sample.corrected_gt == "" else input_elem.update(
            f'{current_sample.corrected_gt}')
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
    image_elem.update(data=get_img_data(filename, first=True))
    # update window with filename
    filename_display_elem.update(f'{sample_list[i].prediction} ; {sample_list[i].difference_token} ; {sample_list[0].img_name}')  # filename
    # update page display
    file_num_display_elem.update('File {} of {}'.format(i + 1, num_files))
    # update gt
    # input_elem.update(f'{flist0[i].gt}')

window.close()
