import os.path

import vcr

from contentpacks.khanacademy import retrieve_kalite_content_data, \
    retrieve_kalite_exercise_data, retrieve_kalite_topic_data
from contentpacks.utils import NODE_FIELDS_TO_TRANSLATE, \
    download_and_cache_file, flatten_topic_tree, translate_nodes, \
    translate_assessment_item_text

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
