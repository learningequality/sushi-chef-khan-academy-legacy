import logging
import os
import vcr
from babel.messages.catalog import Catalog
from hypothesis import assume, given
from hypothesis.strategies import integers, lists, sampled_from, sets, text, \
    tuples

from contentpacks.khanacademy import _combine_catalogs, _get_video_ids, \
    retrieve_dubbed_video_mapping, retrieve_html_exercises, \
    retrieve_kalite_content_data, retrieve_kalite_exercise_data, \
    retrieve_kalite_topic_data, retrieve_translations, retrieve_subtitles, apply_dubbed_video_map
from contentpacks.utils import CONTENT_FIELDS_TO_TRANSLATE, \
    EXERCISE_FIELDS_TO_TRANSLATE, TOPIC_FIELDS_TO_TRANSLATE, translate_contents, \
    translate_exercises, translate_topics
from helpers import cvcr
from helpers import generate_node_list

logging.basicConfig()
logging.getLogger("vcr").setLevel(logging.DEBUG)


class Test_apply_dubbed_video_map:

    def test_apply_dubbed(self, test_content, correct_answer):
       
        test_dubbed = {"y2-uaPiyoxc":"lhS-nvcK8Co"}
        test_dict = list(apply_dubbed_video_map(test_content, test_dubbed))
        assert test_dict
        assert isinstance(test_dict, list)
        assert test_dict == correct_answer


class Test_retrieve_subtitles:
    @cvcr.use_cassette()
    def test_incorrect_youtube_id(self):
        incorrect_list = ["aaa"]
        empty_list = retrieve_subtitles(incorrect_list, force=True)
        test_list = []
        assert not empty_list
        assert isinstance(empty_list, list)

    @cvcr.use_cassette()
    def test_correct_youtube_id(self):
        correct_list = ["y2-uaPiyoxc"]
        filled_list = retrieve_subtitles(correct_list, force=True)
        test_list = ["y2-uaPiyoxc"]
        assert filled_list
        assert isinstance(filled_list, list)

    @cvcr.use_cassette()
    def test_correct_and_incorrect_youtube_id(self):
        mixed_list =  ["y2-uaPiyoxc", "asdadsafa"]
        filled_list = retrieve_subtitles(mixed_list, force=True)
        test_list = ["y2-uaPiyoxc"]
        assert filled_list
        assert isinstance(filled_list, list)
        assert filled_list == test_list

    @cvcr.use_cassette()
    def test_directory_made(self):
        correct_list = ["y2-uaPiyoxc"]
        youtube_id = correct_list[0]
        file_suffix = '.vtt'
        retrieve_subtitles(correct_list, force=True)
        path = os.getcwd() + "/build/subtitles/en/" + youtube_id + file_suffix
        assert os.path.exists(path)

    @cvcr.use_cassette()
    def test_correct_youtube_id_and_incorrect_langpack(self):
        correct_list = ["y2-uaPiyoxc"]
        empty_list = retrieve_subtitles(correct_list,"falselang", force=True)
        test_list = []
        assert not empty_list
        assert isinstance(empty_list, list)

class Test_retrieve_dubbed_mappings:
    
    @cvcr.use_cassette(serializer="yaml")
    def test_correct_youtube_id_dubbed(self):
        correct_list = ["y2-uaPiyoxc"]
        correct_dictionary = {"y2-uaPiyoxc" : "lhS-nvcK8Co"}
        test_call = retrieve_dubbed_video_mapping(correct_list, "de")
        assert isinstance(test_call, dict)
        assert test_call
        assert test_call == correct_dictionary

    @cvcr.use_cassette(serializer="yaml")
    def test_correct_youtube_id_incorrect_lang_dubbed(self):
        correct_list = ["y2-uaPiyoxc"]
        test_call = retrieve_dubbed_video_mapping(correct_list, "asdasda")
        assert isinstance(test_call, dict)
        assert not test_call

    @cvcr.use_cassette(serializer="yaml")
    def test_incorrect_youtube_id_dubbed(self):
        incorrect_list = ["asfbsaf"]
        test_call = retrieve_dubbed_video_mapping(incorrect_list, "de")
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


class Test__combine_catalogs:

    @given(text(), integers(), integers())
    def test_total_message_count(self, txt, msgcount1, msgcount2):
        assume(0 < msgcount1 <= msgcount2 <= 100)

        catalog1 = Catalog()
        for n in range(msgcount1):
            catalog1.add(id=str(n), string=txt)

        catalog2 = Catalog()
        for n in range(msgcount2):
            catalog2.add(id=str(n + 1000), string=txt)  # we add 1000 to make sure the ids are unique

        newcatalog = _combine_catalogs(catalog1, catalog2)

        # the +1 is to account for the empty message, which gets added automatically.
        assert len(list(newcatalog)) == msgcount1 + msgcount2 + 1


class Test__get_video_ids:

    @given(lists(tuples(text(min_size=1), sampled_from(["Exercise", "Video", "Topic"]))))
    def test_given_list_returns_only_videos(self, contents):
        content = {id: {"kind": kind} for id, kind in contents}
        video_count = len([id for id in content if content[id]["kind"] == "Video"])

        assert len(_get_video_ids(content)) == video_count

    @vcr.use_cassette("tests/fixtures/cassettes/kalite/contents.json.yml")
    def test_returns_something_in_production_json(self):
        """
        Since we know that test_given_list_returns_only_videos works, then
        we only need to check that we return something for the actual contents.json
        to make sure we're reading the right attributes.
        """
        content_data = retrieve_kalite_content_data()

        assert _get_video_ids(content_data)


class Test_retrieve_kalite_content_data:

    @vcr.use_cassette("tests/fixtures/cassettes/kalite/contents.json.yml")
    def test_returns_dict(self):
        content_data = retrieve_kalite_content_data()
        assert isinstance(content_data, dict)


class Test_retrieve_kalite_exercise_data:

    @vcr.use_cassette("tests/fixtures/cassettes/kalite/exercises.json.yml")
    def test_returns_dict(self):
        exercise_data = retrieve_kalite_exercise_data()
        assert isinstance(exercise_data, dict)


@vcr.use_cassette("tests/fixtures/cassettes/kalite/contents.json.yml")
def _get_all_video_ids():
    """
    Test utility function so we only need to generate the list of video
    ids once, and then assign that to an instance variable. We
    wrap it as a function instead of assigning the value of
    retrieve_kalite_content_data directly so we can use the
    cassette system to cache the results, avoiding an expensive
    http request.

    """
    content_data = retrieve_kalite_content_data()

    ids = _get_video_ids(content_data)

    # return a tuple, to make sure it gets never modified.
    ids_tuple = tuple(ids)

    # just take the first 10 ids -- don't run too many
    return ids_tuple[:10]


class Test_retrieve_dubbed_video_mapping:

    video_list = _get_all_video_ids()

    @vcr.use_cassette("tests/fixtures/cassettes/khanacademy/video_api.yml", record_mode="new_episodes")
    @given(sets(elements=sampled_from(video_list)))
    def test_returns_dict_given_singleton_list(self, video_ids):

        dubbed_videos_set = set(
            retrieve_dubbed_video_mapping(
                video_ids,
                lang="de"
            ))

        assert dubbed_videos_set.issubset(video_ids)


class Test_translating_kalite_data:

    @classmethod
    @vcr.use_cassette("tests/fixtures/cassettes/translate_exercises.yml", filter_query_parameters=["key"])
    def setup_class(cls):
        cls.ka_catalog = retrieve_translations("khanacademy", "dummy", lang_code="es-ES", includes="*learn.*.po")

    @vcr.use_cassette("tests/fixtures/cassettes/translate_topics.yml")
    def test_translate_topics(self):
        topic_data = retrieve_kalite_topic_data()
        translated_topic_data = translate_topics(
            topic_data,
            self.ka_catalog,
        )

        def _test_topic_children(translated_topic, untranslated_topic):
            for field in TOPIC_FIELDS_TO_TRANSLATE:
                untranslated_fieldval = untranslated_topic.get(field)
                translated_fieldval = translated_topic.get(field)

                assert (translated_fieldval ==
                        self.ka_catalog.msgid_mapping.get(
                            untranslated_fieldval,
                            untranslated_fieldval)
                )

                for translated, untranslated in zip(translated_topic.get("children", []),
                                                    untranslated_topic.get("children", [])):
                    _test_topic_children(translated, untranslated)

        _test_topic_children(translated_topic_data, topic_data)

    @vcr.use_cassette("tests/fixtures/cassettes/translate_contents.yml")
    def test_translate_contents(self):
        content_data = retrieve_kalite_content_data()
        translated_content_data = translate_contents(
            content_data,
            self.ka_catalog,
        )

        for content_id in translated_content_data:
            for field in CONTENT_FIELDS_TO_TRANSLATE:
                translated_fieldval = translated_content_data[content_id][field]
                untranslated_fieldval = content_data[content_id][field]
                assert translated_fieldval == self.ka_catalog.msgid_mapping.get(untranslated_fieldval, "")

    @vcr.use_cassette("tests/fixtures/cassettes/translate_exercises.yml", filter_query_parameters=["key"])
    def test_translating_kalite_exercise_data(self):
        exercise_data = retrieve_kalite_exercise_data()
        ka_catalog = retrieve_translations("khanacademy", "dummy", lang_code="es-ES", includes="*learn.*.po")

        translated_exercise_data = translate_exercises(exercise_data, ka_catalog)

        for exercise_id in translated_exercise_data:
            for field in EXERCISE_FIELDS_TO_TRANSLATE:
                translated_fieldval = translated_exercise_data[exercise_id][field]
                untranslated_fieldval = exercise_data[exercise_id][field]
                assert translated_fieldval == ka_catalog.msgid_mapping.get(untranslated_fieldval, "")


class Test_retrieve_html_exercises:

    @vcr.use_cassette("tests/fixtures/cassettes/test_retrieve_html_exercises_setup.yml")
    def setup(self):
        self.exercise_data = retrieve_kalite_exercise_data()
        self.khan_exercises = [key for key, e in self.exercise_data.items() if not e.get("uses_assessment_items")]
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
