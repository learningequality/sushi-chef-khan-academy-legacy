import vcr
from babel.messages.catalog import Catalog
from hypothesis import assume, given
from hypothesis.strategies import integers, text, lists, tuples, sampled_from, \
    sets

from contentpacks.contentpacks import _combine_catalogs, _get_video_ids, \
    retrieve_dubbed_video_mapping, retrieve_kalite_content_data, \
    retrieve_translations


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
