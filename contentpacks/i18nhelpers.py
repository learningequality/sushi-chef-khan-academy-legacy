
import collections
import os

import requests


LangpackResources = collections.namedtuple(
    "LangpackResources",
    ["topics",
     "contents",
     "exercises",
     "subtitles",
     "kalite_catalog",
     "ka_catalog",
     "dubbed_video_mapping"
    ])


def retrieve_language_resources(lang: str, version: str) -> LangpackResources:

    content_data = retrieve_kalite_content_data()
    exercise_data = retrieve_kalite_exercise_data()
    topic_data = retrieve_kalite_topic_data()

    subtitle_list = retrieve_subtitles(lang)

    # retrieve KA Lite po files from CrowdIn
    crowdin_project_name = "ka-lite"
    crowdin_secret_key = os.environ["KALITE_CROWDIN_SECRET_KEY"]
    includes = [version]
    kalite_catalog = retrieve_translations(crowdin_project_name, crowdin_secret_key, includes)

    # retrieve Khan Academy po files from CrowdIn
    crowdin_project_name = "khanacademy"
    crowdin_secret_key = os.environ["KA_CROWDIN_SECRET_KEY"]
    includes = [version]
    ka_catalog = retrieve_translations(crowdin_project_name, crowdin_secret_key, includes)

    dubbed_video_mapping = retrieve_dubbed_video_mapping(lang)

    return LangpackResources(topic_data, content_data, exercise_data, subtitle_data, kalite_catalog, ka_catalog, dubbed_video_mapping)


def retrieve_translations(crowdin_project_name, crowdin_secret_key, lang_code="en", includes=None) -> polib.POFile:

    request_url_template = "https://api.crowdin.com/api/project/{project_id}/download/{lang_code}.zip?key={key}"
    request_url = request_url_template.format(
        project_id=crowdin_project_name,
        lang_code=lang_code,
        key=crowdin_secret_key,
    )

    zip_path = download_and_cache_file(url)


def download_and_cache_file(url, cachedir=None, ignorecache=False) -> str:
    "Download the given url if it's not saved in cachedir. Returns the path to
    the file. Always download the file if ignorecache is True.
    "
    if not cachedir:
        cachedir = os.path.join(os.getcwd(), "build")

    path = os.path.join(cachedir, os.path.basename(url))

    if ignorecache or not os.path.exists(path):
        urllib.urlretrieve(url, path)

    return path
