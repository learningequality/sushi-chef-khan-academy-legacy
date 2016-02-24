"""
extract_khan_assessment

Creates a khan_assessment.zip, fully compatible with KA Lite 0.15.x and below,
from a full content pack.

Usage:
  extract_khan_assessment.py <content-pack-path> [<out-path>]

"""
import logging
import zipfile
from docopt import docopt
from pathlib import Path


ASSESSMENT_FOLDER_IN_ZIP = "khan/"  # Note: this should just be imported from the contentpacks module


def extract_khan_assessment(contentpackpath: Path, outpath: Path):
    with zipfile.ZipFile(str(contentpackpath)) as cf,\
         zipfile.ZipFile(str(outpath), "w") as of:

        items = list(i for i in cf.namelist()
                     if ASSESSMENT_FOLDER_IN_ZIP in i)

        logging.info("Writing {} items to {}".format(
            len(items),
            outpath)
        )
        for item in items:
            bytes = cf.read(item)

            # the relative_to call removes the leading khan/ in the item's path
            new_item_name = Path(item).relative_to(ASSESSMENT_FOLDER_IN_ZIP)

            of.writestr(str(new_item_name), bytes)

        logging.info("great success.")


def main():
    args = docopt(__doc__)

    logging.basicConfig()
    contentpackpath = Path(args["<content-pack-path>"])
    outpath = Path(args["<out-path>"] or "out/khan_assessment.zip")
    outpath = outpath.expanduser()

    extract_khan_assessment(contentpackpath, outpath)


if __name__ == "__main__":
    main()
