
import collections
import fnmatch
import gc
import glob
import os
import polib
import shutil
import subprocess
import tempfile
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
    includes = []
    ka_catalog = retrieve_translations(crowdin_project_name, crowdin_secret_key)

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


def retrieve_translations(crowdin_project_name, crowdin_secret_key, lang_code="en", includes="*.po") -> polib.POFile:

    request_url_template = ("https://api.crowdin.com/api/"
                            "project/{project_id}/download/"
                            "{lang_code}.zip?key={key}")
    request_url = request_url_template.format(
        project_id=crowdin_project_name,
        lang_code=lang_code,
        key=crowdin_secret_key,
    )

    zip_path = download_and_cache_file(request_url)
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


def retrieve_kalite_topic_data(url=None):
    """
    Retrieve the KA Lite topics.json file in the master branch.  If
    url is given, download from that url instead.
    """
    if not url:
        url = "https://raw.githubusercontent.com/learningequality/ka-lite/master/data/khan/topics.json"

    path = download_and_cache_file(url)
    with open(path) as f:
        return json.load(f)


def retrieve_kalite_exercise_data(url=None) -> dict:
    """
    Retrieve the KA Lite exercises.json file in the master branch.  If
    url is given, download from that url instead.
    """
    print("downloading exercise data")
    if not url:
        url = "https://raw.githubusercontent.com/learningequality/ka-lite/master/data/khan/exercises.json"

    path = download_and_cache_file(url)
    with open(path) as f:
        return json.load(f)
