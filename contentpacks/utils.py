import copy
import os
import urllib.parse
import urllib.request
from enum import Enum
from urllib.parse import urlparse

import polib


class NodeType(Enum):
    exercise = "Exercise"
    video = "Video"
    topic = "Topic"

EXERCISE_FIELDS_TO_TRANSLATE = [
    "description",
    "title",
    "display_name",
]

CONTENT_FIELDS_TO_TRANSLATE = [
    "title",
    "description",
]

TOPIC_FIELDS_TO_TRANSLATE = [
    "title",
    "description",
]


def download_and_cache_file(url, cachedir=None, ignorecache=False) -> str:
    """
    Download the given url if it's not saved in cachedir. Returns the
    path to the file. Always download the file if ignorecache is True.
    """

    if not cachedir:
        cachedir = os.path.join(os.getcwd(), "build")

    os.makedirs(cachedir, exist_ok=True)

    path = os.path.join(cachedir, os.path.basename(urlparse.urlparse(url).path))

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


def translate_topics(topic_data: dict, catalog: polib.POFile) -> dict:
    topic_data = copy.deepcopy(topic_data)

    def _translate_topic(topic):
        for field in TOPIC_FIELDS_TO_TRANSLATE:
            fieldval = topic.get(field)
            if field in topic:
                topic[field] = catalog.msgid_mapping.get(fieldval, fieldval)

        topic['children'] = [_translate_topic(child) for child in topic.get('children', [])]
        return topic

    _translate_topic(topic_data)
    return topic_data


def translate_contents(content_data: dict, catalog: polib.POFile) -> dict:
    content_data = copy.deepcopy(content_data)

    for key, content in content_data.items():
        for field in CONTENT_FIELDS_TO_TRANSLATE:
            msgid = content[field]
            content_data[key][field] = catalog.msgid_mapping.get(msgid, "")

    return content_data
