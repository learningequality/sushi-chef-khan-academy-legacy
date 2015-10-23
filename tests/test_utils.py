import os.path
import vcr

from contentpacks.utils import download_and_cache_file


class Test_download_and_cache_file:

    @vcr.use_cassette("tests/fixtures/cassettes/generic_request.yml")
    def test_returns_existing_file(self):
        url = "https://google.com"
        path = download_and_cache_file(url)

        assert os.path.exists(path)
