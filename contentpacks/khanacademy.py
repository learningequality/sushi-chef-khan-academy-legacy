
import collections
import copy
import filecmp
import fnmatch
import gc
import glob
import os
import shutil
import subprocess
import urllib
import tempfile
import zipfile
from multiprocessing.pool import ThreadPool as Pool

import polib
import requests
import ujson
from babel.messages.catalog import Catalog
from babel.messages.pofile import read_po

from contentpacks.utils import download_and_cache_file


NUM_PROCESSES = 5


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


# monkey patch polib.POEntry.merge
def new_merge(self, other):
    """
    Add the non-plural msgstr of `other` rather than an empty string.

    Basically, re-add the change in
    https://github.com/learningequality/ka-lite/commit/9f0aa49579a5d4c98df548863d20a252ed93220e
    but using monkey patching rather than editing the source file directly.
    """
    self.old_merge(other)
    self.msgstr = other.msgstr if other.msgstr else self.msgstr

POEntry_class = polib.POEntry
POEntry_class.old_merge = POEntry_class.merge
POEntry_class.merge = new_merge


def retrieve_language_resources(version: str, sublangargs: dict) -> LangpackResources:

    content_data = retrieve_kalite_content_data()
    exercise_data = retrieve_kalite_exercise_data()
    topic_data = retrieve_kalite_topic_data()

    video_ids = list(content_data.keys())
    # subtitle_list = retrieve_subtitles(video_ids, lang)
    subtitle_list = []
    # dubbed_video_mapping = retrieve_dubbed_video_mapping(video_ids, lang)
    dubbed_video_mapping = []

    # retrieve KA Lite po files from CrowdIn
    interface_lang = sublangargs["interface_lang"]
    if interface_lang == "en":
        kalite_catalog = {}
        ka_catalog = {}
    else:
        crowdin_project_name = "ka-lite"
        crowdin_secret_key = os.environ["KALITE_CROWDIN_SECRET_KEY"]
        includes = version
        kalite_catalog = retrieve_translations(crowdin_project_name, crowdin_secret_key, lang_code=sublangargs["interface_lang"], includes=includes, force=True)

        # retrieve Khan Academy po files from CrowdIn
        crowdin_project_name = "khanacademy"
        crowdin_secret_key = os.environ["KA_CROWDIN_SECRET_KEY"]
        includes = []
        ka_catalog = retrieve_translations(crowdin_project_name, crowdin_secret_key, lang_code=sublangargs["content_lang"], force=True)

    return LangpackResources(topic_data, content_data, exercise_data, subtitle_list, kalite_catalog, ka_catalog, dubbed_video_mapping)


def retrieve_subtitles(videos: list, lang="en", force=False) -> list:
    #videos => contains list of youtube ids
    """return list of youtubeids that were downloaded"""
    downloaded_videos = []
    not_downloaded_videos = []
    for youtube_id in videos:
        print("trying to download subtitle for %s" % youtube_id)
        request_url = "https://www.amara.org/api2/partners/videos/?format=json&video_url=http://www.youtube.com/watch?v=%s" % (
            youtube_id
        )

        try:
            response =  requests.get(request_url)
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            print("Skipping {}".format(youtube_id))
            continue

        content = ujson.loads(response.content)
        if not content["objects"]:
            not_downloaded_videos.append(youtube_id)
            continue
        else:
            amara_id = content["objects"][0]["id"]
            subtitle_download_uri = "https://www.amara.org/api/videos/%s/languages/%s/subtitles/?format=vtt" %(amara_id, lang)
            try:
                response_code = urllib.request.urlopen(subtitle_download_uri)

            except urllib.error.HTTPError:
                continue
            file_dir = os.path.join(os.getcwd(), "build", "subtitles", lang)
            filename = "{}.vtt".format(youtube_id)
            download_and_cache_file(subtitle_download_uri, file_dir, filename=filename, ignorecache=force)
            downloaded_videos.append(youtube_id)

    return downloaded_videos


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
        print("retrieving dubbed video mapping for %s" % video)
        url = url_template.format(video_id=video, lang=lang)

        r = requests.get(url)
        r.raise_for_status()

        deets = r.json()

        if isinstance(deets, dict) and deets["translated_youtube_lang"] == lang:
            dubbed_video_mapping[video] = deets["translated_youtube_id"]

    return dubbed_video_mapping


def retrieve_translations(crowdin_project_name, crowdin_secret_key, lang_code="en", force=False, includes="*.po") -> polib.POFile:

    request_url_template = ("https://api.crowdin.com/api/"
                            "project/{project_id}/download/"
                            "{lang_code}.zip?key={key}")
    request_url = request_url_template.format(
        project_id=crowdin_project_name,
        lang_code=lang_code,
        key=crowdin_secret_key,
    )
    print(request_url)
    zip_path = download_and_cache_file(request_url, ignorecache=force)
    zip_extraction_path = tempfile.mkdtemp()

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(zip_extraction_path)

    all_filenames = glob.iglob(
        os.path.join(zip_extraction_path, "**"),
        recursive=True
    )
    filenames = fnmatch.filter(all_filenames, includes)

    # use the polib library, since it's much faster at concatenating
    # po files.  it doesn't have a dict interface though, so we'll
    # reread the file using babel.Catalog.
    with tempfile.NamedTemporaryFile() as f:
        main_pofile = polib.POFile(fpath=f.name)

        for filename in filenames:
            pofile = polib.pofile(filename)
            main_pofile.merge(pofile)

        for entry in main_pofile:
            entry.obsolete = False

        main_pofile.save()

    shutil.rmtree(zip_extraction_path)

    # add convenience dict for mapping a msgid to msgstr
    main_pofile.msgid_mapping = {m.msgid: m.msgstr for m in main_pofile if m.translated()}
    # main_pofile.msgid_mapping = {m.msgid: m.msgstr for m in main_pofile }

    return main_pofile


def _combine_catalogs(*catalogs):
    catalog = Catalog()

    for oldcatalog in catalogs:
        print("processing %s" % oldcatalog)
        catalog._messages.update(oldcatalog._messages)
        # manually call the gc here so we don't occupy too much
        # memory, and avoid having one huge gc in the future by
        # dumping a po file after it's read
        gc.collect()

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


def retrieve_kalite_content_data(url=None, force=False) -> dict:
    """
    Retrieve the KA Lite contents.json file in the master branch.  If
    url is given, download from that url instead.
    """
    if not url:
        url = "https://raw.githubusercontent.com/learningequality/ka-lite/master/data/khan/contents.json"

    path = download_and_cache_file(url, ignorecache=force)
    with open(path) as f:
        return ujson.load(f)


def retrieve_kalite_topic_data(url=None, force=False):
    """
    Retrieve the KA Lite topics.json file in the master branch.  If
    url is given, download from that url instead.
    """
    if not url:
        url = "https://raw.githubusercontent.com/learningequality/ka-lite/master/data/khan/topics.json"

    path = download_and_cache_file(url, ignorecache=force)
    with open(path) as f:
        return ujson.load(f)


def retrieve_kalite_exercise_data(url=None, force=False) -> dict:
    """
    Retrieve the KA Lite exercises.json file in the master branch.  If
    url is given, download from that url instead.
    """
    print("downloading exercise data")
    if not url:
        url = "https://raw.githubusercontent.com/learningequality/ka-lite/master/data/khan/exercises.json"

    path = download_and_cache_file(url, ignorecache=force)
    with open(path) as f:
        return ujson.load(f)


def apply_dubbed_video_map(content_data: dict, dubmap: dict) -> dict:
    # TODO: stub. Implement more fully next time
    return copy.deepcopy(content_data)


def retrieve_html_exercises(exercises: [str], lang: str, force=False) -> (str, [str]):
    """
    Return a 2-tuple with the first element pointing to the path the exercise files are stored,
    and the second element a list of exercise ids that have html exercises.
    """
    BUILD_DIR = os.path.join(os.getcwd(), "build", lang)
    EN_BUILD_DIR = os.path.join(os.getcwd(), "build", "en")
    EXERCISE_DOWNLOAD_URL_TEMPLATE = ("https://es.khanacademy.org/"
                                      "khan-exercises/exercises/{id}.html?lang={lang}")

    def _download_html_exercise(exercise_id):
        """
        Download an exercise and return its exercise id *if* the
        downloaded url from the selected language is different from the english version.
        """
        lang_url = EXERCISE_DOWNLOAD_URL_TEMPLATE.format(id=exercise_id, lang=lang)
        en_url = EXERCISE_DOWNLOAD_URL_TEMPLATE.format(id=exercise_id, lang="en")
        try:
            lang_file = download_and_cache_file(lang_url, cachedir=BUILD_DIR, ignorecache=force)
            en_file = download_and_cache_file(en_url, cachedir=EN_BUILD_DIR, ignorecache=force)
            if not filecmp.cmp(lang_file, en_file, shallow=False):
                return exercise_id
        except urllib.error.HTTPError:
            return None

    pool = Pool(processes=NUM_PROCESSES)
    translated_exercises = pool.map(_download_html_exercise, exercises)
    # filter out Nones, since it means we got an error downloading those exercises
    result = [e for e in translated_exercises if e]
    return (BUILD_DIR, result)
