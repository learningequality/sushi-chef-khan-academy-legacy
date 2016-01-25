import collections
import copy
import filecmp
import fnmatch
import gc
import glob
import logging
import os
import re
import shutil
import urllib
import tempfile
import zipfile
from collections import OrderedDict
from functools import reduce
from multiprocessing.pool import ThreadPool as Pool
import polib
import requests
import json
import ujson

from contentpacks.utils import download_and_cache_file, Catalog, cache_file

NUM_PROCESSES = 5

LangpackResources = collections.namedtuple(
    "LangpackResources",
    ["node_data",
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
    node_data = retrieve_kalite_data()

    video_ids = list(content_data.keys())
    # subtitle_list = retrieve_subtitles(video_ids, lang)
    subtitle_list = []
    # dubbed_video_mapping = retrieve_dubbed_video_mapping(video_ids, lang)
    dubbed_video_mapping = []

    # retrieve KA Lite po files from CrowdIn
    interface_lang = sublangargs["interface_lang"]
    if interface_lang == "en":
        kalite_catalog = Catalog()
        ka_catalog = Catalog()
    else:
        crowdin_project_name = "ka-lite"
        crowdin_secret_key = os.environ["KALITE_CROWDIN_SECRET_KEY"]

        includes = "*{}*.po".format(version)
        kalite_catalog = retrieve_translations(crowdin_project_name, crowdin_secret_key,
                                               lang_code=sublangargs["interface_lang"], includes=includes, force=True)

        # retrieve Khan Academy po files from CrowdIn
        crowdin_project_name = "khanacademy"
        crowdin_secret_key = os.environ["KA_CROWDIN_SECRET_KEY"]
        includes = []
        ka_catalog = retrieve_translations(crowdin_project_name, crowdin_secret_key,
                                           lang_code=sublangargs["content_lang"], force=True)

    return LangpackResources(node_data, subtitle_list, kalite_catalog, ka_catalog,
                             dubbed_video_mapping)


def retrieve_subtitles(videos: list, lang="en", force=False) -> list:
    # videos => contains list of youtube ids
    """return list of youtubeids that were downloaded"""
    downloaded_videos = []
    not_downloaded_videos = []
    for youtube_id in videos:
        print("trying to download subtitle for %s" % youtube_id)
        request_url = "https://www.amara.org/api2/partners/videos/?format=json&video_url=http://www.youtube.com/watch?v=%s" % (
            youtube_id
        )

        try:
            response = requests.get(request_url)
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
            subtitle_download_uri = "https://www.amara.org/api/videos/%s/languages/%s/subtitles/?format=vtt" % (
            amara_id, lang)
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


def retrieve_translations(crowdin_project_name, crowdin_secret_key, lang_code="en", force=False,
                          includes="*.po") -> polib.POFile:
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

    msgid_mapping = Catalog(main_pofile)

    return msgid_mapping


def _get_video_ids(node_data: list) -> [str]:
    """
    Returns a list of video ids given the KA content dict.
    """
    video_ids = list(node.get("id") for node in node_data if node.get("kind") == "Video")
    return sorted(video_ids)


first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


def convert_camel_case(name) -> str:
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()


def convert_all_nodes_to_camel_case(nodes) -> list:
    for i, node in enumerate(nodes):
        new_node = {}
        for k, v in node.items():
            new_node[convert_camel_case(k)] = v
        nodes[i] = new_node
    return nodes


# Khan Academy specific blacklists

slug_blacklist = ["new-and-noteworthy", "talks-and-interviews", "coach-res"]  # not relevant
slug_blacklist += ["cs", "towers-of-hanoi"]  # not (yet) compatible
slug_blacklist += ["cc-third-grade-math", "cc-fourth-grade-math", "cc-fifth-grade-math", "cc-sixth-grade-math",
                   "cc-seventh-grade-math", "cc-eighth-grade-math"]  # common core
slug_blacklist += ["MoMA", "getty-museum", "stanford-medicine", "crash-course1", "mit-k12", "hour-of-code",
                   "metropolitan-museum", "bitcoin", "tate", "crash-course1", "crash-course-bio-ecology",
                   "british-museum", "aspeninstitute", "asian-art-museum", "amnh", "nova"]  # partner content

# TODO(jamalex): re-check these videos later and remove them from here if they've recovered
slug_blacklist += ["mortgage-interest-rates", "factor-polynomials-using-the-gcf", "inflation-overview",
                   "time-value-of-money", "changing-a-mixed-number-to-an-improper-fraction",
                   "applying-the-metric-system"]  # errors on video downloads


# 'Mortgage interest rates' at http://s3.amazonaws.com/KA-youtube-converted/vy_pvstdBhg.mp4/vy_pvstdBhg.mp4...
# 'Inflation overview' at http://s3.amazonaws.com/KA-youtube-converted/-Z5kkfrEc8I.mp4/-Z5kkfrEc8I.mp4...
# 'Factor expressions using the GCF' at http://s3.amazonaws.com/KA-youtube-converted/_sIuZHYrdWM.mp4/_sIuZHYrdWM.mp4...
# 'Time value of money' at http://s3.amazonaws.com/KA-youtube-converted/733mgqrzNKs.mp4/733mgqrzNKs.mp4...
# 'Applying the metric system' at http://s3.amazonaws.com/KA-youtube-converted/CDvPPsB3nEM.mp4/CDvPPsB3nEM.mp4...
# 'Mixed numbers: changing to improper fractions' at http://s3.amazonaws.com/KA-youtube-converted/xkg7370cpjs.mp4/xkg7370cpjs.mp4...

slug_key = {
    "Topic": "slug",
    "Video": "readable_id",
    "Exercise": "name",
}

def modify_slugs(nodes) -> list:
    for node in nodes:
        node["slug"] = node.get(slug_key.get(node.get("kind")))
    return nodes

id_key = {
    "Topic": "slug",
    "Video": "youtube_id",
    "Exercise": "name",
}

def modify_ids(nodes) -> list:
    for node in nodes:
        node["id"] = node.get(id_key.get(node.get("kind")))
    return nodes

def apply_black_list(nodes) -> list:
    return [node for node in nodes if node.get("slug") not in slug_blacklist]

def group_by_slug(count_dict, item):
    # Build a dictionary, keyed by slug, of items that share that slug
    if item.get("slug") in count_dict:
        count_dict[item.get("slug")].append(item)
    else:
        count_dict[item.get("slug")] = [item]
    return count_dict

def create_paths_remove_orphans_and_empty_topics(nodes) -> list:
    node_dict = {node.get("id"): node for node in nodes}
    # Set the slug on the root node to "khan"
    node_dict["x00000000"]["slug"] = "khan"

    node_list = []

    def recurse_nodes(node, parent_path=""):

        """
        :param node: dict
        :param parent_path: str
        """
        node["path"] = parent_path + node.get("slug") + "/"

        children = node.pop("child_data", [])

        if children:
            children = [node_dict.get(child.get("id")) for child in children if node_dict.get(child.get("id"))]

            counts = reduce(group_by_slug, children, {})
            for items in counts.values():
                # Slug has more than one item!
                if len(items) > 1:
                    i = 1
                    # Rename the items
                    for item in items:
                        if item.get("kind") != "Video":
                            # Don't change video slugs, as that will break internal links from KA.
                            item["slug"] = item["slug"] + "_{i}".format(i=i)
                            item["path"] = node.get("path") + item["slug"] + "/"
                            i += 1

        for child in children:
            recurse_nodes(child, node.get("path"))

        if children or node.get("kind") != "Topic":
            node_list.append(node)

    recurse_nodes(node_dict["x00000000"])

    return node_list

@cache_file
def download_and_clean_kalite_data(url, path) -> str:
    data = requests.get(url)
    attempts = 1
    while data.status_code != 200 and attempts <= 5:
        data = requests.get(url)
        attempts += 1

    if data.status_code != 200:
        raise requests.exceptions.RequestException

    node_data = ujson.loads(data.content)

    # Convert all keys of nodes to snake case from camel case.
    for key in node_data:
        node_data[key] = convert_all_nodes_to_camel_case(node_data[key])

    # Remove any topic nodes that are hidden, deleted, or set to 'do_not_publish'
    # Also remove those flags from the nodes themselves.

    topic_nodes = []

    for node in node_data["topics"]:
        hidden = node.pop("hide")
        dnp = node.pop("do_not_publish")
        deleted = node.pop("deleted")
        # We want to remove all of these, except the root node,
        # the only node we do hide, but we use for defining the overall KA channel
        if not (hidden or dnp or deleted) or node.get("id") == "x00000000":
            topic_nodes.append(node)

    node_data["topics"] = topic_nodes

    # Hack to hardcode the mp4 format flag on Videos.
    for node in node_data["videos"]:
        node["format"] = "mp4"

    # Flatten node_data

    node_data = [node for node_list in node_data.values() for node in node_list]

    # Modify slugs by kind to give more readable URLs

    node_data = modify_slugs(node_data)

    # Remove blacklisted items

    node_data = apply_black_list(node_data)

    # Create paths, deduplicate slugs, remove orphaned content and childless topics

    node_data = create_paths_remove_orphans_and_empty_topics(node_data)

    # Modify id keys to match KA Lite id formats

    node_data = modify_ids(node_data)

    # Save node_data to disk

    with open(path, "w") as f:
        return ujson.dump(node_data, f)


topic_attributes = [
    'childData',
    'deleted',
    'description',
    'doNotPublish',
    'hide',
    'id',
    'kind',
    'slug',
    'title'
]

exercise_attributes = [
    'allAssessmentItems',
    'curatedRelatedVideos',
    'description',
    'displayName',
    'fileName',
    'id',
    'kind',
    'name',
    'prerequisites',
    'slug',
    'title',
    'usesAssessmentItems'
]

video_attributes = [
    'description',
    'downloadSize',
    'duration',
    'id',
    'imageUrl',
    'keywords',
    'kind',
    'licenseName',
    'readableId',
    'relatedExerciseUrl',
    'relativeUrl',
    'sha',
    'slug',
    'title',
    'youtubeId'
]


def retrieve_kalite_data(lang=None, force=False) -> list:
    """
    Retrieve the KA content data direct from KA.
    """
    if lang:
        url = "http://www.khanacademy.org/api/v2/topics/topictree?lang={lang}&projection={projection}".format(lang=lang)
    else:
        url = "http://www.khanacademy.org/api/v2/topics/topictree?projection={projection}"

    projection = OrderedDict([
        ("topics", [OrderedDict((key, 1) for key in topic_attributes)]),
        ("exercises", [OrderedDict((key, 1) for key in exercise_attributes)]),
        ("videos", [OrderedDict((key, 1) for key in video_attributes)])
    ])

    url = url.format(projection=json.dumps(projection))

    node_data_path = download_and_clean_kalite_data(url, ignorecache=force, filename="nodes.json")

    with open(node_data_path, 'r') as f:
        node_data = ujson.load(f)

    return node_data


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
