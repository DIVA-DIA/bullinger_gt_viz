from pathlib import Path
from typing import List

from dataclasses import dataclass

img_types = (".png", ".jpg", "jpeg", ".tiff", ".bmp")


@dataclass
class Sample:
    server_path: Path
    img_name: str
    gt: str
    prediction: str
    difference_token: int
    difference_word: int
    corrected_gt: str = ""
    path: Path = None
    checked: bool = False

    def __repr__(self):
        self.corrected_gt = self.gt if self.corrected_gt == "" else self.corrected_gt
        return f"{self.path / self.img_name} \t {self.corrected_gt} \t {self.gt}"


class Samples(List[Sample]):

    def __init__(self):
        super().__init__()

    def find_by_name(self, name: str):
        for s in self:
            if s.img_name == name:
                return s
        return None

    def append(self, item: Sample) -> None:
        if item.path.is_file() and item.path.suffix in img_types:
            super().append(item)

    def save_as_tsv(self, output_path: Path):
        with output_path.open("w") as f:
            f.writelines("\n".join([str(s) for s in self]))

