import vcr
from babel.messages.catalog import Catalog
from hypothesis import assume, given
from hypothesis.strategies import integers, text

from contentpacks.contentpacks import _combine_catalogs, retrieve_translations


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
