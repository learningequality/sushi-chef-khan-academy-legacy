import copy
import os
import polib
import urllib.request


EXERCISE_FIELDS_TO_TRANSLATE = [
    "description",
    "title",
    "display_name",
]


def download_and_cache_file(url, cachedir=None, ignorecache=False) -> str:
    """
    Download the given url if it's not saved in cachedir. Returns the
    path to the file. Always download the file if ignorecache is True.
    """

    if not cachedir:
        cachedir = os.path.join(os.getcwd(), "build")

    os.makedirs(cachedir, exist_ok=True)

    path = os.path.join(cachedir, os.path.basename(url))

    if ignorecache or not os.path.exists(path):
        urllib.request.urlretrieve(url, path)

    return path


def translate_exercises(exercise_data: dict, catalog: polib.POFile) -> dict:
    # fully copy, so we don't need mess with anyone else using
    # exercise_data in its pristine form
    exercise_data = copy.deepcopy(exercise_data)

    for key, exercise in exercise_data.items():
        for field in EXERCISE_FIELDS_TO_TRANSLATE:
            msgid = exercise[field]
            exercise_data[key][field] = catalog.msgid_mapping.get(msgid, "")

    return exercise_data
