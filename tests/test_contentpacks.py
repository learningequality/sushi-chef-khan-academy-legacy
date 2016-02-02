import logging
import os
import vcr
from hypothesis import given
from hypothesis.strategies import lists, sampled_from, text, \
    tuples

from contentpacks.khanacademy import _get_video_ids, \
    retrieve_dubbed_video_mapping, retrieve_html_exercises, \
    retrieve_kalite_data, retrieve_translations, retrieve_subtitles, apply_dubbed_video_map, \
    retrieve_all_assessment_item_data, retrieve_assessment_item_data, \
    clean_assessment_item, localize_image_urls, localize_content_links, prune_assessment_items
from contentpacks.models import AssessmentItem
from contentpacks.utils import NODE_FIELDS_TO_TRANSLATE, translate_nodes, Catalog, NodeType

logging.basicConfig()
logging.getLogger("vcr").setLevel(logging.DEBUG)


class Test_apply_dubbed_video_map:

    def test_apply_dubbed(self):
        input_id = "y2-uaPiyoxc"
        output_id = "lhS-nvcK8Co"
        test_content = [{"video_id": input_id, "youtube_id": input_id}]

        test_dubbed = {input_id: output_id}
        test_list, test_count = apply_dubbed_video_map(test_content, test_dubbed, [], "de")
        assert test_list
        assert isinstance(test_list, list)
        assert test_list[0]["video_id"] == output_id
        assert test_list[0]["youtube_id"] == output_id
        assert test_count == 1


class Test_retrieve_subtitles:
    @vcr.use_cassette()
    def test_incorrect_youtube_id(self):
        incorrect_list = ["aaa"]
        empty_list = retrieve_subtitles(incorrect_list, force=True)
        assert not empty_list
        assert isinstance(empty_list, list)

    @vcr.use_cassette()
    def test_correct_youtube_id(self):
        correct_list = ["y2-uaPiyoxc"]
        filled_list = retrieve_subtitles(correct_list, force=True)
        assert filled_list
        assert isinstance(filled_list, list)

    @vcr.use_cassette()
    def test_correct_and_incorrect_youtube_id(self):
        mixed_list = ["y2-uaPiyoxc", "asdadsafa"]
        filled_list = retrieve_subtitles(mixed_list, force=True)
        test_list = ["y2-uaPiyoxc"]
        assert filled_list
        assert isinstance(filled_list, list)
        assert filled_list == test_list

    @vcr.use_cassette()
    def test_directory_made(self):
        correct_list = ["y2-uaPiyoxc"]
        youtube_id = correct_list[0]
        file_suffix = '.vtt'
        retrieve_subtitles(correct_list, force=True)
        path = os.getcwd() + "/build/subtitles/en/" + youtube_id + file_suffix
        assert os.path.exists(path)

    @vcr.use_cassette()
    def test_correct_youtube_id_and_incorrect_langpack(self):
        correct_list = ["y2-uaPiyoxc"]
        empty_list = retrieve_subtitles(correct_list, "falselang", force=True)
        assert not empty_list
        assert isinstance(empty_list, list)

class Test_retrieve_dubbed_mappings:
    
    @vcr.use_cassette(serializer="yaml")
    def test_only_dubbed(self):
        test_call = retrieve_dubbed_video_mapping("de")
        assert isinstance(test_call, dict)
        assert test_call
        for key, val in test_call.items():
            assert key != val, "Key and value were identical"

    @vcr.use_cassette(serializer="yaml")
    def test_english_no_dubbed(self):
        test_call = retrieve_dubbed_video_mapping("en")
        assert isinstance(test_call, dict)
        assert not test_call


class Test_retrieve_translations:

    # Note, the CrowdIn request below has been cached by vcr, avoiding
    # the need for the crowdin key. If you do delete the file below,
    # then you need the key in your environment to successfully make
    # the request.
    @vcr.use_cassette("tests/fixtures/cassettes/crowdin/kalite/es.zip.yml")
    def test_returns_list_of_po_files(self):
        project_id = "ka-lite"
        project_key = "dummy"
        catalog = retrieve_translations(project_id, project_key)

        assert isinstance(catalog, Catalog)


class Test__get_video_ids:

    @given(lists(tuples(text(min_size=1), sampled_from(["Exercise", "Video", "Topic"]))))
    def test_given_list_returns_only_videos(self, contents):
        contents = [{"kind": kind, "id": content_id} for content_id, kind in contents]
        video_count = len([node for node in contents if node.get("kind") == "Video"])

        assert len(_get_video_ids(contents)) == video_count

    @vcr.use_cassette("tests/fixtures/cassettes/kalite/node_data.json.yml")
    def test_returns_something_in_production_json(self):
        """
        Since we know that test_given_list_returns_only_videos works, then
        we only need to check that we return something for the actual contents.json
        to make sure we're reading the right attributes.
        """
        data = retrieve_kalite_data()

        assert _get_video_ids(data)


class Test_retrieve_kalite_data:

    @vcr.use_cassette("tests/fixtures/cassettes/kalite/node_data.json.yml")
    def test_returns_dict(self):
        data = retrieve_kalite_data()
        assert isinstance(data, list)


class Test_retrieve_assessment_item_data:

    def setup(self):

        with vcr.use_cassette("tests/fixtures/cassettes/kalite/node_data.json.yml"):
            node_data = retrieve_kalite_data()
            self.assess_node = next(node for node in node_data if node.get("all_assessment_items"))
            self.assessment_item = self.assess_node.get("all_assessment_items")[0].get("id")

    def test_clean_assessment_item(self):
        data = {
            "test": "no",
            "item_data": "yes!",
            "id": "100001",
            "author_names": "author, author!",
            "shouldn'tbehere": 'nothere',
        }
        data = clean_assessment_item(data)

        assert all(a == b for a, b in zip(sorted(data.keys()), sorted(AssessmentItem._meta.get_field_names())))

    def test_retrieve_assessment_item_return_dict(self):
        with vcr.use_cassette("tests/fixtures/cassettes/kalite/assessment_item_data.json.yml", record_mode="all"):
            data, paths = retrieve_assessment_item_data(self.assessment_item)
        assert isinstance(data, dict), "Item data is not of kind dict"

    def test_retrieve_assessment_item_return_list(self):
        with vcr.use_cassette("tests/fixtures/cassettes/kalite/assessment_item_data.json.yml", record_mode="all"):
            data, paths = retrieve_assessment_item_data(self.assessment_item)
        assert isinstance(paths, list), "Paths are not returned as a list"

    def test_retrieve_assessment_item_files_exist(self):
        with vcr.use_cassette("tests/fixtures/cassettes/kalite/assessment_item_data.json.yml", record_mode="all"):
            data, paths = retrieve_assessment_item_data(self.assessment_item)
        for path in paths:
            assert isinstance(path, str), "Path is not of type str"
            assert os.path.exists(path), "Downloaded file does not exist"

    def test_retrieve_all_assessment_item_return_list_of_dicts(self):
        with vcr.use_cassette("tests/fixtures/cassettes/kalite/assessment_item_data.json.yml", record_mode="all"):
            data, paths = retrieve_all_assessment_item_data(node_data=[self.assess_node])
        for datum in data:
            assert isinstance(datum, dict), "Data is not of type dict"

    def test_retrieve_all_assessment_item_return_list_of_str(self):
        with vcr.use_cassette("tests/fixtures/cassettes/kalite/assessment_item_data.json.yml", record_mode="all"):
            data, paths = retrieve_all_assessment_item_data(node_data=[self.assess_node])
        for path in paths:
            assert isinstance(path, str), "Path is not of type str"

    def test_image_url_converted(self):
        url_string = "A string with http://example.com/cat_pics.gif"
        expected_string = "A string with /content/khan/cat/cat_pics.gif"
        assert expected_string == localize_image_urls({"item_data": url_string})["item_data"]

    def test_multiple_image_urls_in_one_string_converted(self):
        url_string = "A string with http://example.com/cat_pics.JPEG http://example.com/cat_pics2.gif"
        expected_string = "A string with /content/khan/cat/cat_pics.JPEG /content/khan/cat/cat_pics2.gif"
        assert expected_string == localize_image_urls({"item_data": url_string})["item_data"]

    def test_content_link_converted(self):
        link_string = "(and so that is the correct answer).**\\n\\n[Watch this video to review](https://www.khanacademy.org/humanities/history/ancient-medieval/Ancient/v/standard-of-ur-c-2600-2400-b-c-e)"
        expected_string = "(and so that is the correct answer).**\\n\\n[Watch this video to review](/learn/khan/test-prep/ap-art-history/ancient-mediterranean-AP/ancient-near-east-a/standard-of-ur-c-2600-2400-b-c-e/)"
        assert expected_string  == localize_content_links({"item_data": link_string})["item_data"]

    def test_bad_content_link_removed(self):
        link_string = "Wrong!\n\n**[Watch video to review](https://www.khanacademy.org/humanities/art-history/v/the-penguin-king-has-risen)**\n\nThat's a wrap!"
        expected_string = "Wrong!\n\n\n\nThat's a wrap!"
        assert expected_string  == localize_content_links({"item_data": link_string})["item_data"]

    def test_remove_non_live_assessment_items(self):
        test_data = [{"uses_assessment_items": True, "all_assessment_items": [{"live": False}, {"live": True}]}]
        out_data = prune_assessment_items(test_data)
        assert len(out_data) == 1, "prune_assessment_items does not return single node"
        assert len(out_data[0].get("all_assessment_items")) == 1, "all_assessment_items wrong length"

    def test_remove_non_live_assessment_item_exercise(self):
        test_data = [{"uses_assessment_items": True, "all_assessment_items": [{"live": False}]}]
        out_data = prune_assessment_items(test_data)
        assert len(out_data) == 0, "prune_assessment_items returns exercise with no assessment items"

    def test_not_remove_non_assessment_item_nodes(self):
        test_data = [{"uses_assessment_items": False}]
        out_data = prune_assessment_items(test_data)
        assert len(out_data) == 1, "prune_assessment_items filters non-asessment item nodes"

@vcr.use_cassette("tests/fixtures/cassettes/kalite/node_data.json.yml")
def _get_all_video_ids():
    """
    Test utility function so we only need to generate the list of video
    ids once, and then assign that to an instance variable. We
    wrap it as a function instead of assigning the value of
    retrieve_kalite_content_data directly so we can use the
    cassette system to cache the results, avoiding an expensive
    http request.

    """
    content_data = retrieve_kalite_data()

    ids = _get_video_ids(content_data)

    # return a tuple, to make sure it gets never modified.
    ids_tuple = tuple(ids)

    # just take the first 10 ids -- don't run too many
    return ids_tuple[:10]


class Test_retrieve_dubbed_video_mapping:

    def test_returns_dict(self):
        with vcr.use_cassette("tests/fixtures/cassettes/khanacademy/video_api.yml", record_mode="new_episodes"):
            dubbed_videos = retrieve_dubbed_video_mapping("de")

        assert isinstance(dubbed_videos, dict)


class Test_translating_kalite_data:

    @classmethod
    @vcr.use_cassette("tests/fixtures/cassettes/translate_exercises.yml", filter_query_parameters=["key"])
    def setup_class(cls):
        cls.ka_catalog = retrieve_translations("khanacademy", "dummy", lang_code="es-ES", includes="*learn.*.po")

    @vcr.use_cassette("tests/fixtures/cassettes/translate_topics.yml")
    def test_translate_nodes(self):
        node_data = retrieve_kalite_data()
        translated_node_data = translate_nodes(
            node_data,
            self.ka_catalog,
        )

        for translated_node, untranslated_node in zip(translated_node_data,
                                                    node_data):
            for field in NODE_FIELDS_TO_TRANSLATE:
                untranslated_fieldval = untranslated_node.get(field)
                translated_fieldval = translated_node.get(field)

                assert (translated_fieldval ==
                        self.ka_catalog.get(
                            untranslated_fieldval,
                            untranslated_fieldval)
                )


class Test_retrieve_html_exercises:

    @vcr.use_cassette("tests/fixtures/cassettes/test_retrieve_html_exercises_setup.yml")
    def setup(self):
        self.exercise_data = retrieve_kalite_data()
        self.khan_exercises = [e.get("id") for e in self.exercise_data if not e.get("uses_assessment_items")\
                               and e.get("kind") == "Exercise"]
        self.khan_exercises.sort()

    @vcr.use_cassette("tests/fixtures/cassettes/test_retrieve_html_exercises.yml")
    def test_creates_folder_with_contents(self):
        exercises = sorted(self.khan_exercises)[:5]  # use only first five for fast testing
        exercise_path, retrieved_exercises = retrieve_html_exercises(exercises, lang="es")

        assert retrieved_exercises  # not empty
        assert set(retrieved_exercises).issubset(self.khan_exercises)
        assert os.path.exists(exercise_path)

    @vcr.use_cassette("tests/fixtures/cassettes/test_retrieve_html_exercises_2.yml")
    def test_doesnt_return_exercises_without_translation(self):
        # The expected behaviour from KA's API is that it would return
        # the english version of an exercise if either a translated
        # exercise for the given language doesn't exist, or the
        # language is unsupported.
        exercise = self.khan_exercises[0]
        lang = "aaa"            # there's no language with code aaa... I hope?

        path, retrieved_exercises = retrieve_html_exercises([exercise], lang, force=True)

        assert not retrieved_exercises

    @vcr.use_cassette("tests/fixtures/cassettes/test_retrieve_html_exercises_3.yml")
    def test_returns_exercise_with_translation(self):
        # espanol has almost complete
        # translation. Assuming this specific
        # exercise has one
        lang = "es"
        exercise = self.khan_exercises[0]

        path, retrieved_exercises = retrieve_html_exercises([exercise], lang, force=True)

        assert retrieved_exercises == [exercise]
