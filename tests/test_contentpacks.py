import vcr
from babel.messages.catalog import Catalog
from hypothesis import assume, given
from hypothesis.strategies import integers, text, lists, tuples, sampled_from

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


class Test_retrieve_dubbed_video_mapping:

    @vcr.use_cassette("tests/fixtures/cassettes/kalite/contents.json.yml")
    def test_returns_a_subset_of_all_videos(self):
        content_data = retrieve_kalite_content_data()
        all_videos = _get_video_ids(content_data)

        dubbed_videos = set(
            retrieve_dubbed_video_mapping(
                all_videos,
                lang="de"
            ))

        assert dubbed_videos.issubset(all_videos)
