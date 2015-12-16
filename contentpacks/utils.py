import copy
import os
import urllib.parse
import urllib.request
from urllib.parse import urlparse
from contentpacks.models import Item
from peewee import Using, SqliteDatabase

import polib
import ujson
import zipfile
import tempfile
import pathlib


class UnexpectedKindError(Exception):
    pass


class NotTranslatable(Exception):
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

NODE_FIELDS_TO_TRANSLATE = [
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
        filename = os.path.basename(urlparse(url).path)

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

        node = copy.copy(node)
        for field in NODE_FIELDS_TO_TRANSLATE:
            original_text = node[field]
            try:
                node[field] = catalog.msgid_mapping[original_text]
            except KeyError:
                print("could not translate {field} for {title}".format(field=field, title=node["title"]))

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
    def gettext(s):
        """
        Specialized gettext function that raises NotTranslatable when no
        translation for s has been found.
        """
        try:
            trans = catalog.msgid_mapping[s]
        except KeyError:
            raise NotTranslatable("String has no translation: {}".format(s))

        return trans

    for id, item in items.items():
        item = copy.copy(item)

        item_data = ujson.loads(item["item_data"])
        try:
            translated_item_data = smart_translate_item_data(item_data, gettext)
        except NotTranslatable:
            continue
        else:
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
    if isinstance(item_data, str):
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


def remove_untranslated_exercises(nodes, html_ids, translated_assessment_data):
    item_data_ids = set(translated_assessment_data.keys())
    html_ids = set(html_ids)

    def is_translated_exercise(ex):

        ex_id = ex["id"]
        if ex_id in html_ids:  # translated html exercise
            return True
        elif ex["uses_assessment_items"]:
            for assessment_raw in ex["all_assessment_items"]:
                item_data = ujson.loads(assessment_raw)
                assessment_id = item_data["id"]
                if assessment_id in item_data_ids:
                    continue
                else:
                    return False
            return True

    for slug, node in nodes:
        if node["kind"] != NodeType.exercise:
            yield slug, node
        elif is_translated_exercise(node):
            yield slug, node
        else:
            continue


def bundle_language_pack(dest, nodes, frontend_catalog, backend_catalog):
    with zipfile.ZipFile(dest, "w") as zf, tempfile.NamedTemporaryFile() as dbf:
        db = SqliteDatabase(dbf.name)
        db.connect()

        nodes = convert_dicts_to_models(nodes)
        nodes = list(save_models(nodes, db)) # we have to make sure to force
                                             # the evaluation of each
                                             # save_models call, in order to
                                             # avoid nesting them.
        nodes = populate_parent_foreign_keys(nodes)
        list(save_models(nodes, db))
        db.close()
        dbf.flush()

        save_catalog(frontend_catalog.msgid_mapping, zf, "frontend.mo")
        save_catalog(backend_catalog.msgid_mapping, zf, "backend.mo")
        # save_subtitles(subtitle_path, zf)

        save_db(db, zf)

    return dest


def convert_dicts_to_models(nodes):

    def _make_extra_fields_value(present_fields, node_dict):
        """
        Generate the JSON string that goes into an item's extra_fields value.
        Do this by looking at the model's columns and then adding those values
        not in the columns into the extra_fields.
        """
        fields_diff = set(node_dict.keys()) - set(present_fields)

        extra_fields = {}
        for field in fields_diff:
            extra_fields[field] = node_dict[field]

        return ujson.dumps(extra_fields)

    def convert_dict_to_model(node):
        item = Item(**node)

        item.__dict__.update(**node)
        item.available = False
        item.extra_fields = _make_extra_fields_value(
            item._meta.get_field_names(),
            node
        )

        return item

    yield from (convert_dict_to_model(node) for _, node in nodes)


def save_models(nodes, db):
    """
    Save all the models in nodes into the db specified.
    """
    # aron: I didn't bother writing tests for this, since it's such a simple
    # function!
    db.create_table(Item, safe=True)
    with Using(db, [Item]):
        for node in nodes:
            try:
                node.save()
            except Exception as e:
                print("Cannot save {path}, exception: {e}".format(path=node.path, e=e))

            yield node


def save_catalog(catalog: dict, zf: zipfile.ZipFile, name: str):

    mofile = polib.MOFile()
    for msgid, msgstr in catalog.items():
        entry = polib.POEntry(msgid=msgid, msgstr=msgstr)
        mofile.append(entry)

    # zf.writestr(name, mofile.to_binary())
    with tempfile.NamedTemporaryFile() as f:
        mofile.save(f.name)
        zf.write(f.name, name)


def populate_parent_foreign_keys(nodes):
    node_keys = {node.slug: node for node in nodes}

    for node in node_keys.values():
        path = pathlib.Path(node.path)
        parent_slug = path.parent.name
        try:
            parent = node_keys[parent_slug]
            node.parent = parent
        except KeyError:
            print("{path} is an orphan.".format(path=node.path))

        yield node


def save_db(db, zf):
    zf.write(db.database, "content.db")


def separate_exercise_types(node_data):
    node_data = list(node_data)

    def _is_html_exercise(node):
        return node["kind"] == NodeType.exercise and not node["uses_assessment_items"]

    def _is_assessment_exercise(node):
        return node["kind"] == NodeType.exercise and node["uses_assessment_items"]

    return (id for id, n in node_data if _is_html_exercise(n)), \
        (id for id, n in node_data if _is_assessment_exercise(n)), \
        node_data
