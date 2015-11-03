
import collections
import fnmatch
import os
import requests
import ujson as json
import zipfile

from contentpacks.utils import download_and_cache_file
from babel.messages.catalog import Catalog
from babel.messages.pofile import read_po


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


def retrieve_subtitles(videos: list, lang="en") -> dict:
    return {}


def retrieve_dubbed_video_mapping(video_ids: [str], lang: str) -> dict:
    """
    Returns a dictionary mapping between the english id, and its id for
    the dubbed video version given the language.

    Note (aron): optimize later by doing only one request to the topic
    tree and then filtering videos from there.
    """
    url_template = ("http://www.khanacademy.org/api/v1/"
                    "videos/{video_id}?lang={lang}")

    dubbed_video_mapping = {}

    for video in video_ids:
        url = url_template.format(video_id=video, lang=lang)

        r = requests.get(url)
        r.raise_for_status()

        deets = r.json()

        if deets["translated_youtube_lang"] == lang:
            dubbed_video_mapping[video] = deets["translated_youtube_id"]

    return dubbed_video_mapping


def retrieve_translations(crowdin_project_name, crowdin_secret_key, lang_code="en", includes="*.po") -> Catalog:

    request_url_template = ("https://api.crowdin.com/api/"
                            "project/{project_id}/download/"
                            "{lang_code}.zip?key={key}")
    request_url = request_url_template.format(
        project_id=crowdin_project_name,
        lang_code=lang_code,
        key=crowdin_secret_key,
    )

    zip_path = download_and_cache_file(request_url)

    catalogs = []
    with zipfile.ZipFile(zip_path) as zf:
        filenames = fnmatch.filter(zf.namelist(), includes)
        for filename in filenames:
            f = zf.open(filename)
            pofile = read_po(f)
            catalogs.append(pofile)

    return _combine_catalogs(*catalogs)


def _combine_catalogs(*catalogs):
    catalog = Catalog()

    for oldcatalog in catalogs:
        catalog._messages.update(oldcatalog._messages)

    return catalog


def _get_video_ids(content_data: dict) -> [str]:
    """
    Returns a list of video ids given the KA content dict.
    """
    video_ids = list(key for key in content_data.keys() if content_data[key]["kind"] == "Video")
    return sorted(video_ids)


def _retrieve_ka_topic_tree(lang="en"):
    """
    Retrieve the full topic tree straight from KA.
    """
    url = None
    path = download_and_cache_file


def retrieve_kalite_content_data(url=None) -> dict:
    """
    Retrieve the KA Lite contents.json file in the master branch.  If
    url is given, download from that url instead.
    """
    if not url:
        url = "https://raw.githubusercontent.com/learningequality/ka-lite/master/data/khan/contents.json"

    path = download_and_cache_file(url)
    with open(path) as f:
        return json.load(f)
