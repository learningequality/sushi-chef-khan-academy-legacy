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
    retrieve_kalite_topic_data, retrieve_translations
from contentpacks.utils import CONTENT_FIELDS_TO_TRANSLATE, \
    EXERCISE_FIELDS_TO_TRANSLATE, TOPIC_FIELDS_TO_TRANSLATE, translate_contents, \
    translate_exercises, translate_topics


logging.basicConfig()
logging.getLogger("vcr").setLevel(logging.DEBUG)


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


@vcr.use_cassette("tests/fixtures/cassettes/test_retrieve_html_exercises.yml")
def test_retrieve_html_exercises():
    exercise_data = retrieve_kalite_exercise_data()
    khan_exercises = [key for key, e in exercise_data.items() if not e.get("uses_assessment_items")]
    exercises = sorted(khan_exercises)[:5]  # use only first five for fast testing
    exercise_path, retrieved_exercises = retrieve_html_exercises(exercises, lang="es")

    assert set(retrieved_exercises).issubset(khan_exercises)
    assert os.path.exists(exercise_path)
