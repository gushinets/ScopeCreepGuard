"""Reproduce static regular Noto Sans from the retained OFL variable source."""

from pathlib import Path
from shutil import copyfile

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "assets/fonts"
TARGET = ROOT / "src/scope_guard/infrastructure/documents/assets"


def main():
    TARGET.mkdir(parents=True, exist_ok=True)
    font = TTFont(SOURCE / "noto-sans-variable.ttf", recalcTimestamp=False)
    axes = {axis.axisTag: axis.defaultValue for axis in font["fvar"].axes}
    axes["wght"] = 400
    static = instantiateVariableFont(font, axes, inplace=True)
    static.save(TARGET / "noto-sans.ttf")
    copyfile(SOURCE / "noto-sans-bold.ttf", TARGET / "noto-sans-bold.ttf")
    copyfile(SOURCE / "OFL-noto-sans.txt", TARGET / "OFL-noto-sans.txt")


if __name__ == "__main__":
    main()
