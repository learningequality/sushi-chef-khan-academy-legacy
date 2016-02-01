import copy
import os
import pkgutil
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


NODE_FIELDS_TO_TRANSLATE = [
    "title",
    "description",
    "display_name",
]


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
    def func_wrapper(url, cachedir=None, ignorecache=False, filename=None):
            if not cachedir:
                cachedir = os.path.join(os.getcwd(), "build")

            os.makedirs(cachedir, exist_ok=True)

            if not filename:
                filename = os.path.basename(urlparse(url).path)

            path = os.path.join(cachedir, filename)

            if ignorecache or not os.path.exists(path):
                func(url, path)

            return path

    return func_wrapper


@cache_file
def download_and_cache_file(url, path) -> str:
    """
    Download the given url if it's not saved in cachedir. Returns the
    path to the file. Always download the file if ignorecache is True.
    """

    urllib.request.urlretrieve(url, path)


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
                    print("could not translate {field} for {title}".format(field=field, title=node["title"]))

    return nodes


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
            trans = catalog[s]
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

        for field, field_data in item_data.items():
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


def bundle_language_pack(dest, nodes, frontend_catalog, backend_catalog, metadata):
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

        save_catalog(frontend_catalog, zf, "frontend.mo")
        save_catalog(backend_catalog, zf, "backend.mo")
        # save_subtitles(subtitle_path, zf)

        save_db(db, zf)

        save_metadata(zf, metadata)

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

    yield from (convert_dict_to_model(node) for node in nodes)


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
    node_keys = {node.path: node for node in nodes}

    for node in node_keys.values():
        path = pathlib.Path(node.path)
        parent_slug = str(path.parent)
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


def generate_kalite_language_pack_metadata(lang: str, version: str, interface_catalog: Catalog, content_catalog: Catalog):
    """
    Create the language pack metadata based on the files passed in.
    """
    metadata = {
        "code": lang,
        'software_version': version,
        'language_pack_version': 1,
        'percent_translated': interface_catalog.percent_translated,
        'topic_tree_translated': content_catalog.percent_translated,
        'subtitle_count': 0,
        "name": get_lang_name(lang),
        'native_name': get_lang_native_name(lang),
    }

    return metadata


def get_lang_name(lang):
    langlookup = ujson.loads(LANGUAGELOOKUP_DATA)

    try:
        return langlookup[lang]["name"]
    except KeyError:
        print("No name found for {}. Defaulting to DEBUG.".format(lang))
        return "DEBUG"


def get_lang_native_name(lang):
    langlookup = ujson.loads(LANGUAGELOOKUP_DATA)

    try:
        return langlookup[lang]["native_name"]
    except KeyError:
        print("No native name found for {}. Defaulting to DEBUG.".format(lang))
        return "DEBUG"


def save_metadata(zf, metadata):
    dump = ujson.dumps(metadata)
    metadata_name = "metadata.json"
    zf.writestr(metadata_name, dump)

