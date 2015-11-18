import os.path

import vcr

from contentpacks.khanacademy import retrieve_kalite_content_data, \
    retrieve_kalite_exercise_data, retrieve_kalite_topic_data
from contentpacks.utils import download_and_cache_file, flatten_topic_tree


class Test_download_and_cache_file:

    @vcr.use_cassette("tests/fixtures/cassettes/generic_request.yml")
    def test_returns_existing_file(self):
        url = "https://google.com"
        path = download_and_cache_file(url)

        assert os.path.exists(path)


class Test_flatten_topic_tree:

    @vcr.use_cassette("tests/fixtures/cassettes/test_returns_all_contents_and_exercises.yml")
    def test_returns_all_contents_and_exercises(self):
        topic_root = retrieve_kalite_topic_data()
        contents = retrieve_kalite_content_data()
        exercises = retrieve_kalite_exercise_data()

        topic_list = list(flatten_topic_tree(topic_root, contents, exercises))

        assert len(topic_list) >= len(contents) + len(exercises)
