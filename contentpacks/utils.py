import copy
import os
import urllib.parse
import urllib.request
from enum import Enum
from urllib.parse import urlparse

import polib
import ujson

from contentpacks.models import CompatibilityAssessmentItem


from peewee import SqliteDatabase, Using


class UnexpectedKindError(Exception):
    pass


class NodeType:
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



def download_and_cache_file(url, cachedir=None, ignorecache=False, filename=None) -> str:
    """
    Download the given url if it's not saved in cachedir. Returns the
    path to the file. Always download the file if ignorecache is True.
    """

    if not cachedir:
        cachedir = os.path.join(os.getcwd(), "build")

    os.makedirs(cachedir, exist_ok=True)

    if not filename:
        filename = os.path.basename(urlparse.urlparse(url).path)

    path = os.path.join(cachedir, filename)
    
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


def translate_nodes(nodes, catalog):
    """Translates the following fields which are common across all nodes:

    title
    description

    (see NODE_FIELDS_TO_TRANSLATE for a more up-to-date list)

    Note that translation in these fields is nonessential -- meaning
    that even if they're not translated they're not a dealbreaker, and
    thus won't be eliminated from the topic tree.

    """
    for slug, node in nodes:

        for field in NODE_FIELDS_TO_TRANSLATE:
            original_text = node[field]
            node = copy.copy(node)
            node[field] = catalog.msgid_mapping.get(original_text) or original_text

        yield slug, node


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


def flatten_topic_tree(topic_root, contents, exercises):

    def _flatten_topic(node):
        childless_topic = copy.copy(node)
        children = childless_topic.pop("children", [])

        kind = childless_topic["kind"]
        node_id = childless_topic["id"]
        slug = childless_topic["slug"]

        if kind == NodeType.topic:
            # get the slugs of the children so we can refer to them
            children_slugs = [c["slug"] for c in children]
            childless_topic["children"] = children_slugs
            yield slug, childless_topic

        elif kind == NodeType.exercise:
            exercise = exercises[node_id]
            yield slug, exercise

        elif kind == NodeType.video:
            video = contents[node_id]
            yield slug, video

        else:
            raise UnexpectedKindError("Unexpected node kind: {}".format(kind))

        for child in children:
            yield from _flatten_topic(child)

    return _flatten_topic(topic_root)


def translate_assessment_item_text(items: dict, catalog: polib.POFile):
    """
    Expects a dict with assessment ids as key and the item data as
    value, along with a catalog file from retrieve_language_resources
    as translation source. Returns a series of key value pairs with
    the id as key and the translated item data as the value.

    Assessment item translations are considered essential, and thus
    if they're found missing will make that exercise as unavailable.
    """
    # TODO (aronasorman): implement tests
    gettext = lambda s: catalog.msgid_mapping.get(s, "")
    for id, item in items:
        item = copy.copy(item)

        item_data = ujson.loads(item["item_data"])
        translated_item_data = smart_translate_item_data(item_data, gettext)
        item["item_data"] = ujson.dumps(translated_item_data)

        yield id, item



def smart_translate_item_data(item_data: dict, gettext):
    """Auto translate the content fields of a given assessment item data.

    An assessment item doesn't have the same fields; they change
    depending on the question. Instead of manually specifying the
    fields to translate, this function loops over all fields of
    item_data and translates only the content field.

    Requires a gettext function.
    """
    # TODO (aronasorman): implement tests
    # just translate strings immediately
    if isinstance(item_data, basestring):
        return gettext(item_data)

    elif isinstance(item_data, list):
        return map(smart_translate_item_data, item_data)

    elif isinstance(item_data, dict):
        if 'content' in item_data:
            item_data['content'] = gettext(item_data['content']) if item_data['content'] else ""

        for field, field_data in item_data.iteritems():
            if isinstance(field_data, dict):
                item_data[field] = smart_translate_item_data(field_data)
            elif isinstance(field_data, list):
                item_data[field] = map(smart_translate_item_data, field_data)

        return item_data
