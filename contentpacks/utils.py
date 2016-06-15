import copy
import logging
import os
import pkgutil
import re
import requests
from functools import partial
from urllib.parse import urlparse
from contentpacks.models import Item, AssessmentItem
from peewee import Using, SqliteDatabase, fn
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


NODE_FIELDS_TO_TRANSLATE = [
    "title",
    "description",
    "display_name",
]


ASSESSMENT_RESOURCES_ZIP_FOLDER = "khan/"

ASSESSMENT_VERSION_FILENAME = "assessmentitems.version"


LANGUAGELOOKUP_DATA = pkgutil.get_data('contentpacks', "resources/languagelookup.json")


class Catalog(dict):
    """
    Just like a dict, but computes some additional metadata specific to i18n catalog files.
    """

    def __init__(self, pofile=None):
        """
        Extract the strings from the given pofile, and computes the metadata.
        """
        # Add an entry for the empty message
        self[""] = ""
        if not pofile:
            pofile = []
            self.percent_translated = 0
        else:

            self.update({m.msgid: m.msgstr for m in pofile if m.translated()})

            # compute metadata -- needs to be after we add the translated strings
            self.percent_translated = self.compute_translated(pofile)

        super().__init__()

    def compute_translated(self, pofile: polib._BaseFile) -> int:
        """
        Returns the percentage of strings translated. Returned number is between 0
        to 100.

        """
        trans_count = len(self)
        all_strings_count = len(pofile)

        return (trans_count / all_strings_count) * 100


def cache_file(func):
    """
    Execute the decorated function only if the file in question is not already cached.
    Returns the path to the file. Always download the file if ignorecache is True.
    All decorated functions must only accept 2 args, 'url' and 'path'.
    """
    def func_wrapper(url, cachedir=None, ignorecache=False, filename=None, **kwargs):
            if not cachedir:
                cachedir = os.path.join(os.getcwd(), "build")

            if not filename:
                filename = os.path.basename(urlparse(url).path) + urlparse(url).query

            path = os.path.join(cachedir, filename)

            os.makedirs(os.path.dirname(path), exist_ok=True)

            if ignorecache or not os.path.exists(path):
                func(url, path, **kwargs)

            return path

    return func_wrapper


@cache_file
def download_and_cache_file(url: str, path: str, headers: dict={}) -> str:
    """
    Download the given url if it's not saved in cachedir. Returns the
    path to the file. Always download the file if ignorecache is True.
    """

    logging.info("Downloading file from {url}".format(url=url))

    r = requests.get(url, stream=True, headers=headers)
    r.raise_for_status()

    with open(path, "wb") as f:
        for chunk in r.iter_content(1024):
            f.write(chunk)

    return path


def translate_nodes(nodes: list, catalog: Catalog) -> list:
    """Translates all fields across all nodes:

    (see NODE_FIELDS_TO_TRANSLATE for list)

    Note that translation in these fields is nonessential -- meaning
    that even if they're not translated they're not a dealbreaker, and
    thus won't be eliminated from the topic tree.
    """
    nodes = copy.deepcopy(nodes)
    for node in nodes:

        for field in NODE_FIELDS_TO_TRANSLATE:
            msgid = node.get(field)
            if msgid:
                try:
                    node[field] = catalog[msgid]
                except KeyError:
                    logging.debug("could not translate {field} for {title}".format(field=field, title=node["title"]))

    return nodes


def translate_assessment_item_text(items: list, catalog: Catalog):
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
        Convenience function for translating text through the given catalog.
        """
        trans = catalog.get(s) or s

        return trans

    for item in items:
        item = copy.copy(item)

        item_data = ujson.loads(item["item_data"])
        try:
            translated_item_data = smart_translate_item_data(item_data, gettext)
        except NotTranslatable:
            continue
        else:
            item["item_data"] = ujson.dumps(translated_item_data, gettext)
            yield item


def smart_translate_item_data(item_data: dict, gettext):
    """Auto translate the content fields of a given assessment item data.

    An assessment item doesn't have the same fields; they change
    depending on the question. Instead of manually specifying the
    fields to translate, this function loops over all fields of
    item_data and translates only the content field.

    Requires a gettext function.
    """
    translate_item_fn = partial(smart_translate_item_data, gettext=gettext)

    # TODO (aronasorman): implement tests
    # just translate strings immediately
    if isinstance(item_data, str):
        return gettext(item_data)

    elif isinstance(item_data, list):
        return list(map(translate_item_fn, item_data))

    elif isinstance(item_data, dict):
        if 'content' in item_data:
            item_data['content'] = gettext(item_data['content']) if item_data['content'] else ""

        for field, field_data in item_data.items():
            if isinstance(field_data, dict):
                item_data[field] = smart_translate_item_data(field_data, gettext)
            elif isinstance(field_data, list):
                item_data[field] = list(map(translate_item_fn, field_data))

        return item_data


def remove_untranslated_exercises(nodes, html_ids, translated_assessment_data):
    item_data_ids = set([item.get("id") for item in translated_assessment_data])
    html_ids = set(html_ids)

    def is_translated_exercise(ex):

        ex_id = ex["id"]
        if ex_id in html_ids:  # translated html exercise
            return True
        elif ex["uses_assessment_items"]:
            for item_data in ex["all_assessment_items"]:
                assessment_id = item_data["id"]
                if assessment_id in item_data_ids:
                    continue
                else:
                    return False
            return True

    for node in nodes:
        if node["kind"] != NodeType.exercise:
            yield node
        elif is_translated_exercise(node):
            yield node
        else:
            continue


def remove_unavailable_topics(nodes):

    node_dict = {node.get("path"): node for node in nodes}

    node_list = []

    def recurse_nodes(node):

        """
        :param node: dict
        """

        path_re = re.compile(node.get("path") + "[a-z0-9A-Z\-_]+/\Z")

        children = [node_dict[key] for key in node_dict.keys() if path_re.match(key)]

        for child in children:
            recurse_nodes(child)

        if children or node.get("kind") != "Topic":
            node_list.append(node)

    root_key = next(key for key in node_dict.keys() if re.match("[a-z0-9A-Z\-_]+/\Z", key))

    recurse_nodes(node_dict[root_key])

    return node_list


def bundle_language_pack(dest, nodes, frontend_catalog, backend_catalog, metadata, assessment_items, assessment_files, subtitles, html_exercise_path):

    # make sure dest's parent directories exist
    pathlib.Path(dest).parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(dest, "w") as zf, tempfile.NamedTemporaryFile() as dbf:
        db = SqliteDatabase(dbf.name)
        db.connect()

        nodes = convert_dicts_to_models(nodes)
        nodes = mark_exercises_as_available(nodes)
        nodes = list(save_models(nodes, db)) # we have to make sure to force
                                             # the evaluation of each
                                             # save_models call, in order to
                                             # avoid nesting them.
        nodes = list(populate_parent_foreign_keys(nodes))
        list(save_models(nodes, db))

        nodes = recurse_availability_up_tree(nodes, db)
        list(save_models(nodes, db))

        assessment_items = convert_dicts_to_assessment_items(assessment_items)
        list(save_assessment_items(assessment_items, db))

        db.close()
        dbf.flush()

        save_catalog(frontend_catalog, zf, "frontend.mo")
        save_catalog(backend_catalog, zf, "backend.mo")
        # save_subtitles(subtitle_path, zf)

        try:                    # sometimes we have no html exercises
            save_html_exercises(html_exercise_path, zf)
        except FileNotFoundError:
            logging.warning("No html exercises found; skipping.")

        save_db(db, zf)

        save_metadata(zf, metadata)

        for file_path in assessment_files:
            save_assessment_file(file_path, zf)
        write_assessment_version(metadata, zf)

        for subtitle_path in subtitles:
            save_subtitle(subtitle_path, zf)

    return dest


def write_assessment_version(metadata: dict, zf):
    lang = metadata.get("code") or "en"
    if lang != "en":            # Don't write the assessment version for non-en lang packs
        return
    else:
        version = str(metadata.get("software_version", "xx.xx"))
        assessment_version_zip_path = os.path.join(ASSESSMENT_RESOURCES_ZIP_FOLDER, ASSESSMENT_VERSION_FILENAME)
        zf.writestr(assessment_version_zip_path, version)


def save_html_exercises(html_exercise_path, zf):
    logging.info("Saving html exercises in {}".format(html_exercise_path))
    zip_html_exercise_root = pathlib.Path("exercises/")

    html_exercise_path = pathlib.Path(html_exercise_path)

    for exercise_path in html_exercise_path.iterdir():
        exercise_name = exercise_path.name
        zip_exercise_path = zip_html_exercise_root / exercise_name

        zf.writestr(str(zip_exercise_path), exercise_path.read_bytes())


def save_subtitle(path: str, zf: zipfile.ZipFile):
    zip_subtitle_root = pathlib.Path("subtitles/")

    path = pathlib.Path(path)
    name = path.name

    zip_subtitle_path = zip_subtitle_root / name
    zf.write(str(path), str(zip_subtitle_path))


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

        # make sure description is a string, not None
        item.description = item.description or ""

        item.extra_fields = _make_extra_fields_value(
            item._meta.get_field_names(),
            node
        )

        return item

    yield from (convert_dict_to_model(node) for node in nodes)


def mark_exercises_as_available(nodes):
    '''
    Mark all exercises as available. Unavailable exercises should've been
    removed from the topic tree by this point.

    '''
    for node in nodes:
        if node.kind == NodeType.exercise:
            node.available = True
        yield node


def convert_dicts_to_assessment_items(assessment_items):
    yield from (AssessmentItem(**item) for item in assessment_items)


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
                logging.warning("Cannot save {path}, exception: {e}".format(path=node.path, e=e))

            yield node


def save_assessment_items(assessment_items, db):
    """
    Save all the models in nodes into the db specified.
    """
    # aron: I didn't bother writing tests for this, since it's such a simple
    # function!
    db.create_table(AssessmentItem, safe=True)
    with Using(db, [AssessmentItem]):
        for item in assessment_items:
            try:
                item.save()
            except Exception as e:
                logging.warning("Cannot save {id}, exception: {e}".format(id=item.id, e=e))

            yield item


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
    node_keys = {node.path: node for node in nodes}

    orphan_count = 0

    for node in node_keys.values():
        path = pathlib.Path(node.path)
        parent_slug = str(path.parent)
        # topic tree paths end in a slash, but path.parent removes the trailing slash. Re-add it so parent_slug matches the key in node_keys
        parent_slug += "/"
        try:
            parent = node_keys[parent_slug]
            node.parent = parent
        except KeyError:
            orphan_count += 1
            logging.warning("{path} is an orphan. (number {orphan_count})".format(path=node.path, orphan_count=orphan_count))

        yield node


def save_db(db, zf):
    zf.write(db.database, "content.db")


def save_assessment_file(assessment_file, zf):
        zf.write(assessment_file, os.path.join(ASSESSMENT_RESOURCES_ZIP_FOLDER, os.path.basename(os.path.dirname(
            assessment_file)), os.path.basename(assessment_file)))


def separate_exercise_types(node_data):
    node_data = list(node_data)

    def _is_html_exercise(node):
        return node["kind"] == NodeType.exercise and not node["uses_assessment_items"]

    def _is_assessment_exercise(node):
        return node["kind"] == NodeType.exercise and node["uses_assessment_items"]

    return (n['id'] for n in node_data if _is_html_exercise(n)), \
           (n['id'] for n in node_data if _is_assessment_exercise(n)), \
           node_data


def generate_kalite_language_pack_metadata(lang: str, version: str, interface_catalog: Catalog,
                                           content_catalog: Catalog, subtitles: list, dubbed_video_count: int):
    """
    Create the language pack metadata based on the files passed in.
    """

    # language packs are automatically beta if they have no dubbed videos and subtitles
    is_beta = dubbed_video_count == 0 and len(subtitles) == 0

    metadata = {
        "code": lang,
        'software_version': version,
        'language_pack_version': 1,
        'percent_translated': interface_catalog.percent_translated,
        'topic_tree_translated': content_catalog.percent_translated,
        'subtitle_count': len(subtitles),
        "name": get_lang_name(lang),
        'native_name': get_lang_native_name(lang),
        "video_count": dubbed_video_count,
        "beta": is_beta,
    }

    return metadata


def get_lang_name(lang):
    langlookup = ujson.loads(LANGUAGELOOKUP_DATA)

    try:
        return langlookup[lang]["name"]
    except KeyError:
        logging.warning("No name found for {}. Defaulting to DEBUG.".format(lang))
        return "DEBUG"


def get_lang_native_name(lang):
    langlookup = ujson.loads(LANGUAGELOOKUP_DATA)

    try:
        return langlookup[lang]["native_name"]
    except KeyError:
        logging.warning("No native name found for {}. Defaulting to DEBUG.".format(lang))
        return "DEBUG"


def save_metadata(zf, metadata):
    dump = ujson.dumps(metadata)
    metadata_name = "metadata.json"
    zf.writestr(metadata_name, dump)


def recurse_availability_up_tree(nodes, db) -> [Item]:

    logging.info("Marking availability.")

    nodes = list(nodes)

    def _recurse_availability_up_tree(node):

        available = node.available
        if not node.parent:
            return node
        else:
            parent = node.parent
        Parent = Item.alias()
        children = Item.select().join(Parent, on=(Item.parent == Parent.pk)).where(Item.parent == parent.pk)
        if not available:
            children_available = children.where(Item.available == True).count() > 0
            available = children_available

        total_files = children.aggregate(fn.SUM(Item.total_files))

        child_remote = children.where(((Item.available == False) & (Item.kind != "Topic")) | (Item.kind == "Topic")).aggregate(fn.SUM(Item.remote_size))
        child_on_disk = children.aggregate(fn.SUM(Item.size_on_disk))

        if parent.available != available:
            parent.available = available
        if parent.total_files != total_files:
            parent.total_files = total_files
        # Ensure that the aggregate sizes are not None
        if parent.remote_size != child_remote and child_remote:
            parent.remote_size = child_remote
        # Ensure that the aggregate sizes are not None
        if parent.size_on_disk != child_on_disk and child_on_disk:
            parent.size_on_disk = child_on_disk
        if parent.is_dirty():
            parent.save()
            _recurse_availability_up_tree(parent)

        return node

    with Using(db, [Item]):
        # at this point, the only thing that can affect a topic's availability
        # are exercises. Videos and other content's availability can only be
        # determined by what's in the client. However, we need to set total_files
        # and remote_sizes. So, loop over exercises and other content,
        # and skip topics as they will be recursed upwards.
        for node in (n for n in nodes if n.kind != NodeType.topic):
            _recurse_availability_up_tree(node)

    return nodes


def is_video_node_dubbed(video_node: dict, expected_lang: str) -> bool:
    assert 'translated_youtube_lang' in video_node, "We need the " \
        "translated_youtube_lang attribute to figure out if a video is dubbed!"

    video_lang = video_node['translated_youtube_lang']
    return get_primary_language(video_lang) == get_primary_language(expected_lang)


def get_primary_language(lang):
    """
    A language code may come in two parts as per ISO 639-1. For the case of
    pt-BR, the first part would be the primary language (pt) and the second
    one, the country code. This function retruns the primary language part of
    the language code.

    """
    if len(lang) <= 2:          # Already only the primary language
        return lang
    else:
        # lang is something like pt-BR
        # Split the lang code into two parts (pt, BR)
        # And return the first part (pt)
        return lang.\
            split("-")\
            [0]


def remove_assessment_data_with_empty_widgets(assessment_data):
    outed = 0
    for assessment in assessment_data:
        try:
            assessment_id = assessment.get("id")
            item_data = ujson.loads(assessment["item_data"])
            question_data = item_data["question"]

            if question_data.get("widgets"):
                yield assessment
            else:
                outed += 1
                logging.warning("Filtering out assessment {}. Count: {}".format(assessment_id, outed))
        except KeyError as e:
            logging.warning("Got error when checking widgets for assessment data {id}: {e}".format(
                id=assessment_id,
                e=e)
            )


def remove_nonexistent_assessment_items_from_exercises(node_data: list, assessment_data: iter):
    assessment_ids = set(assessment["id"] for assessment in assessment_data)

    for node in node_data:
        if node["kind"] != NodeType.exercise:
            yield node
        else:
            # import pdb; pdb.set_trace()
            try:
                assessment_items = node["all_assessment_items"]
                new_assessment_items = []
                for item in assessment_items:
                    ass_id = item["id"]
                    if ass_id in assessment_ids:
                        new_assessment_items.append(item)
                node["all_assessment_items"] = new_assessment_items
                yield node
            except Exception as e:
                import pdb; pdb.set_trace()
                print(1)
