import os.path

import vcr
import ujson
import tempfile
import zipfile

from contentpacks.khanacademy import retrieve_kalite_data
from contentpacks.models import Item
from contentpacks.utils import NODE_FIELDS_TO_TRANSLATE, \
    download_and_cache_file, translate_nodes, \
    translate_assessment_item_text, NodeType, remove_untranslated_exercises, \
    convert_dicts_to_models, save_catalog, populate_parent_foreign_keys, \
    save_db

from helpers import generate_catalog
from peewee import SqliteDatabase, Using


class Test_download_and_cache_file:

    @vcr.use_cassette("tests/fixtures/cassettes/generic_request.yml")
    def test_returns_existing_file(self):
        url = "https://google.com"
        path = download_and_cache_file(url)

        assert os.path.exists(path)


class Test_translate_nodes:

    @vcr.use_cassette("tests/fixtures/cassettes/kalite/node_data.json.yml")
    def test_translates_selected_fields(self):
        node_data = retrieve_kalite_data()
        node_dict = {node.get("slug"): node for node in node_data}
        catalog = generate_catalog()

        translated_nodes = translate_nodes(node_data, catalog)

        for slug, node in translated_nodes:
            for field in NODE_FIELDS_TO_TRANSLATE:
                translated_fieldval = node.get(field, "")
                untranslated_fieldval = node_dict[slug],get(field, "")
                assert translated_fieldval == catalog.msgid_mapping.get(untranslated_fieldval,
                                                                        untranslated_fieldval)


class Test_translate_assessment_item_text:

    def test_doesnt_return_untranslated_items(self):
        catalog = generate_catalog()

        sample_data = {
            "not_in_catalog": {
                "item_data": '"wala ito sa catalog"'
            },
            "not_translated": {
                "item_data": '"Heart failure"'
            },
            "translated": {
                "item_data": '"Millions"'
            }
        }

        translated = [id for id, _ in translate_assessment_item_text(sample_data, catalog)]

        assert "translated" in translated
        assert "not_in_catalog" not in translated
        assert "not_translated" not in translated


class Test_remove_untranslated_exercise:

    def test_always_returns_videos_and_topics(self):
        self.nodes = [
            ("no-html", {"kind": NodeType.exercise,
                         "id": "1",
                         "uses_assessment_items": False}),
            ("no-assessment", {"kind": NodeType.exercise,
                               "id": "2",
                               "uses_assessment_items": True,
                               "all_assessment_items": []}),

            ("video", {"kind": NodeType.video}),
            ("topic", {"kind": NodeType.topic}),
        ]
        # these don't matter, and can thus be empty
        item_data = {}
        html_ids = set()

        result = set(s for s ,_ in remove_untranslated_exercises(self.nodes, html_ids, item_data))

        assert "video" in result
        assert "topic" in result

    def test_returns_exercise_with_assessment_items(self):
        nodes = [
            ("translated", {"kind": NodeType.exercise,
                            "id": "1",
                            "uses_assessment_items": True,
                            "all_assessment_items": [ujson.dumps({"id": "jebs"})],
            }
            )
        ]

        items = {"jebs": "jebs"}

        exercises = set(k for k,_ in remove_untranslated_exercises(nodes, [], items))

        assert "translated" in exercises

    def test_returns_exercise_with_html(self):
        nodes = [
            ("has-html", {
                "kind": NodeType.exercise,
                "id": "has-html",
                "uses_assessment_items": False
            })
        ]
        html_ids = ["has-html"]

        exercises = set(k for k,_ in remove_untranslated_exercises(nodes, html_ids, {}))

        assert "has-html" in exercises


class Test_convert_dicts_to_models:

    @vcr.use_cassette("tests/fixtures/cassettes/kalite/node_data.json.yml")
    def test_raises_no_errors_on_actual_data(self):
        nodes = retrieve_kalite_data()
        new_nodes = list(convert_dicts_to_models(nodes))

        # see if we can have peewee validate the models


class Test_save_catalog:

    def test_mofile_exists_in_zip(self):
        with tempfile.NamedTemporaryFile() as f:
            zf = zipfile.ZipFile(f, "w")
            name = "test.mo"
            catalog = {"msgid": "msgstr"}

            save_catalog(catalog, zf, name)

            assert name in zf.namelist()


class Test_populate_parent_foreign_keys:

    @vcr.use_cassette("tests/fixtures/cassettes/kalite/node_data.json.yml")
    def test_all_nodes_have_parent_values(self):
        nodes = convert_dicts_to_models(retrieve_kalite_data())
        new_nodes = list(populate_parent_foreign_keys(nodes))

        for node in new_nodes:
            if node.title != "Khan Academy": # aron: maybe there's a better way to find the root node?
                assert node.parent and isinstance(node.parent, Item)


class Test_save_db:

    def test_writes_db_to_archive(self):
        with tempfile.NamedTemporaryFile() as zffobj:
            zf = zipfile.ZipFile(zffobj, "w")

            with tempfile.NamedTemporaryFile() as dbfobj:
                db = SqliteDatabase(dbfobj.name)
                db.connect()
                with Using(db, [Item]):
                    Item.create_table()
                    item = Item(id="test", title="test",
                                description="test", available=False,
                                slug="srug", kind=NodeType.video,
                                path="/test/test")
                    item.save()
                db.close()

                save_db(db, zf)

            zf.close()

            # reopen the db from the zip, see if our object was saved
            with tempfile.NamedTemporaryFile() as f:
                # we should only have one file in the zipfile, the db. Assume
                # that the first file is the db.
                zf = zipfile.ZipFile(zffobj.name)
                dbfobj = zf.open(zf.infolist()[0])
                f.write(dbfobj.read())
                f.seek(0)

                db = SqliteDatabase(f.name)

                with Using(db, [Item]):
                    Item.get(title="test")
