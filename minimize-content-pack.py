"""
minimize-content-pack

Remove assessment items, subtitles and po files from a content pack.

Usage:
  minimize-content-pack.py <old-content-pack-path> <out-path>
"""
import zipfile
from pathlib import Path
from docopt import docopt

ITEMS_TO_TRANSFER = [
    "metadata.json",
    "content.db",
    "backend.mo",
    "frontend.mo",
]


def minimize_content_pack(oldpackpath: Path, outpath: Path):
    with zipfile.ZipFile(str(oldpackpath)) as oldzf,\
         zipfile.ZipFile(str(outpath), "w") as newzf:

        items = list(i for i in oldzf.namelist()
                     for will_be_transferred in ITEMS_TO_TRANSFER
                     if will_be_transferred in i)

        for item in items:
            bytes = oldzf.read(item)
            newzf.writestr(item, bytes)


def main():
    args = docopt(__doc__)

    contentpackpath = Path(args["<old-content-pack-path>"])
    outpath = Path(args["<out-path>"] or
                   "out/minimal.zip")
    outpath = outpath.expanduser()

    minimize_content_pack(contentpackpath, outpath)


if __name__ == "__main__":
    main()
