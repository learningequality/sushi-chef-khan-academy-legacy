import os.path

import vcr
import ujson
import tempfile
import zipfile

from contentpacks.khanacademy import retrieve_kalite_content_data, \
    retrieve_kalite_exercise_data, retrieve_kalite_topic_data
from contentpacks.utils import NODE_FIELDS_TO_TRANSLATE, \
    download_and_cache_file, flatten_topic_tree, translate_nodes, \
    translate_assessment_item_text, NodeType, remove_untranslated_exercises, \
    convert_dicts_to_models, save_catalog

from helpers import cvcr, generate_node_list, generate_catalog


class Test_download_and_cache_file:

    @vcr.use_cassette("tests/fixtures/cassettes/generic_request.yml")
    def test_returns_existing_file(self):
        url = "https://google.com"
        path = download_and_cache_file(url)

        assert os.path.exists(path)


class Test_flatten_topic_tree:

    @cvcr.use_cassette()
    def test_returns_all_contents_and_exercises(self):
        topic_root = retrieve_kalite_topic_data()
        contents = retrieve_kalite_content_data()
        exercises = retrieve_kalite_exercise_data()

        topic_list = list(flatten_topic_tree(topic_root, contents, exercises))

        assert len(topic_list) >= len(contents) + len(exercises)


class Test_translate_nodes:

    def test_translates_selected_fields(self):
        node_data = dict(generate_node_list())
        catalog = generate_catalog()

        translated_nodes = translate_nodes(node_data.items(), catalog)

        for slug, node in translated_nodes:
            for field in NODE_FIELDS_TO_TRANSLATE:
                translated_fieldval = node[field]
                untranslated_fieldval = node_data[slug][field]
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

    def test_raises_no_errors_on_actual_data(self):
        nodes = list(generate_node_list())
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
