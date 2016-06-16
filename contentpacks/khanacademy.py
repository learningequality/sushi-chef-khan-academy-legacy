import collections
import copy
import filecmp
import fnmatch
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
from multiprocessing.pool import ThreadPool
import itertools
import polib
import requests
import json
import ujson
import pkgutil

from math import ceil, log, exp

from contentpacks.utils import NodeType, download_and_cache_file, Catalog, cache_file,\
    is_video_node_dubbed, get_lang_name
from contentpacks.models import AssessmentItem

NUM_PROCESSES = 5

LangpackResources = collections.namedtuple(
    "LangpackResources",
    ["node_data",
     "subtitles",
     "kalite_catalog",
     "ka_catalog",
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


def retrieve_language_resources(version: str, sublangargs: dict, no_subtitles: bool) -> LangpackResources:
    node_data = retrieve_kalite_data(lang=sublangargs["content_lang"], force=True)

    video_ids = [node.get("id") for node in node_data if node.get("kind") == "Video"]
    subtitle_data = retrieve_subtitles(video_ids, sublangargs["subtitle_lang"]) if not no_subtitles else {}

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
                                           lang_code=sublangargs["interface_lang"], force=True)

    return LangpackResources(node_data, subtitle_data, kalite_catalog, ka_catalog)


@cache_file
def retrieve_subtitle_meta_data(url, path):

    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.HTTPError:
        raise

    content = ujson.loads(response.content)

    if not content.get("objects"):
        raise KeyError

    amara_id = content["objects"][0]["id"]

    with open(path, 'w') as f:
        f.write(amara_id)


def retrieve_subtitles(videos: list, lang="en", force=False, threads=NUM_PROCESSES) -> dict:
    # videos => contains list of youtube ids
    """return list of youtubeids that were downloaded"""
    lang = lang.lower()         # Amara likes lowercase codes
    def _download_subtitle_data(youtube_id):

        logging.info("trying to download subtitle for %s" % youtube_id)
        request_url = "https://www.amara.org/api2/partners/videos/?format=json&video_url=http://www.youtube.com/watch?v=%s" % (
            youtube_id
        )

        try:
            amara_id_file = retrieve_subtitle_meta_data(request_url, filename="subtitles/meta_data/{youtube_id}".format(
                youtube_id=youtube_id))
            with open(amara_id_file, 'r') as f:
                amara_id = f.read()
            subtitle_download_uri = "https://www.amara.org/api/videos/%s/languages/%s/subtitles/?format=vtt" % (
                amara_id, lang)
            filename = "subtitles/{lang}/{youtube_id}.vtt".format(lang=lang, youtube_id=youtube_id)
            subtitle_path = download_and_cache_file(subtitle_download_uri, filename=filename, ignorecache=False)
            logging.info("subtitle path: {}".format(subtitle_path))
            return youtube_id, subtitle_path
        except (requests.exceptions.RequestException, KeyError, urllib.error.HTTPError, urllib.error.URLError) as e:
            logging.info("got error while downloading subtitles: {}".format(e))
            pass

    pools = ThreadPool(processes=threads)

    poolresult = pools.map(_download_subtitle_data, videos)
    subtitle_data = dict(s for s in poolresult if s) # remove empty return values

    return subtitle_data


def retrieve_translations(crowdin_project_name, crowdin_secret_key, lang_code="en", force=False,
                          includes="*.po") -> Catalog:
    request_url_template = ("https://api.crowdin.com/api/"
                            "project/{project_id}/download/"
                            "{lang_code}.zip?key={key}")
    export_url_template = ("https://api.crowdin.com/api/"
                            "project/{project_id}/export/"
                            "{lang_code}.zip?key={key}")
    request_url = request_url_template.format(
        project_id=crowdin_project_name,
        lang_code=lang_code,
        key=crowdin_secret_key,
    )
    export_url = request_url_template.format(
        project_id=crowdin_project_name,
        lang_code=lang_code,
        key=crowdin_secret_key,
    )

    logging.info("requesting CrowdIn to rebuild latest translations.")
    try:
        requests.get(export_url)
    except requests.exceptions.RequestException as e:
        logging.warning(
            "Got exception when building CrowdIn translations: {}".format(e)
        )

    logging.debug("Retrieving translations from {}".format(request_url))
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
    "Exercise": "name",
}


def modify_ids(nodes, lang="en") -> list:
    logging.debug("Modifying the ids of the nodes")
    node_video_id_mappings = get_video_id_english_mappings(lang)
    for node in nodes:
        node_id = node["id"]
        if node["kind"] == NodeType.video:
            node["id"] = node_video_id_mappings.get(node_id) or node["youtube_id"]
        else:
            node["id"] = node.get(id_key.get(node.get("kind")))

    return nodes


def get_video_id_english_mappings(lang):
    if lang == "en":
        mapping = {}
    else:
        logging.info("Creating mapping for nodes"
                     " between en and {}".format(lang))

        projection = {"videos": [
            OrderedDict(
                [("youtubeId", 1),
                 ("id", 1)]
            )]}

        url_template = "http://www.khanacademy.org/api/v2/topics/topictree?projection={projection}"
        url = url_template.format(lang=lang, projection=json.dumps(projection))

        while 1:
            try:
                r = requests.get(url)
                r.raise_for_status()
                break
            except requests.exceptions.HTTPError as e:
                logging.warning("Got an error from Khan Academy requesting from their topic tree url: {}".format(e))
                logging.warning("Trying again.")

        english_video_data = r.json()
        english_video_data = english_video_data["videos"]

        mapping = {n["id"]: n["youtubeId"] for n in english_video_data}

    return mapping


def apply_black_list(nodes) -> list:
    return [node for node in nodes if node.get("slug") not in slug_blacklist]


def prune_assessment_items(nodes) -> list:
    node_list = []
    for node in nodes:
        if node.get("uses_assessment_items"):
            assessment_items = []
            for item in node.get("all_assessment_items", []):
                if item.get("live"):
                    assessment_items.append(item)
            node["all_assessment_items"] = assessment_items
            if node.get("all_assessment_items"):
                node_list.append(node)
        else:
            node_list.append(node)

    return node_list


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

    def recurse_nodes(node, parent_path="", node_count=0.0):

        """
        :param node: dict
        :param parent_path: str
        :param node_count: float
        """
        node["path"] = parent_path + node.get("slug") + "/"

        node["sort_order"] = node_count

        logging.debug("Node count: {}".format(node_count))

        children = node.pop("child_data", [])

        if children:
            # Use a deepcopy here, in order to create an entirely separate node, not referencing any child objects
            # This avoids any nested data in the node data being shared across nodes.
            # Our chosen strategy of duplicating content nodes that appear twice in the topic tree requires this.
            children = [copy.deepcopy(node_dict.get(child.get("id"))) for child in children if node_dict.get(child.get("id"))]

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
            node_count += 1
            node_count = recurse_nodes(child, node.get("path"), node_count)

        if children or node.get("kind") != "Topic":
            node_list.append(node)

        return node_count

    recurse_nodes(node_dict["x00000000"])

    return node_list


@cache_file
def download_exercise_data(url, path) -> str:
    data = requests.get(url)

    attempts = 1
    while data.status_code != 200 and attempts <= 5:
        data = requests.get(url)
        attempts += 1

    if data.status_code != 200:
        raise requests.RequestException

    exercise_data = ujson.loads(data.content)

    with open(path, "w") as f:
        ujson.dump(exercise_data, f)


def retrieve_exercise_dict(lang=None, force=False) -> str:
    url = "https://www.khanacademy.org/api/internal/exercises" + ("?lang={lang}".format(lang=lang) if lang else "")

    exercise_data_path = download_exercise_data(url, ignorecache=force, filename="exercises.json")

    with open(exercise_data_path, 'r') as f:
        exercise_data = ujson.load(f)

    return {ex.get("id"): ex for ex in exercise_data}


@cache_file
def download_and_clean_kalite_data(url, path, lang="en") -> str:
    data = requests.get(url)
    attempts = 1
    while data.status_code != 200 and attempts <= 5:
        data = requests.get(url)
        attempts += 1

    if data.status_code != 200:
        raise requests.RequestException("Got error requesting KA data: {}".format(data.content))

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

    # Hack to add basepoints to all Exercise data.
    ex_dict = retrieve_exercise_dict()

    for node in node_data["exercises"]:
        seconds_per_fast_problem = ex_dict.get(node.get("id"), {}).get("seconds_per_fast_problem", 0)
        node["basepoints"] = ceil(7 * log(max(exp(5. / 7), seconds_per_fast_problem)))

        # if not english, prepend language code to file_name attribute of the exercise node
        if lang != "en" and not node["uses_assessment_items"]:
            node["file_name"] = os.path.join(lang, node["file_name"])

    # Flatten node_data

    node_data = [node for node_list in node_data.values() for node in node_list]

    # Modify slugs by kind to give more readable URLs

    node_data = modify_slugs(node_data)

    # Remove blacklisted items

    node_data = apply_black_list(node_data)

    # Remove non-live assessment items and any consequently 'empty' exercises

    node_data = prune_assessment_items(node_data)

    # Create paths, deduplicate slugs, remove orphaned content and childless topics

    node_data = create_paths_remove_orphans_and_empty_topics(node_data)

    # Modify id keys to match KA Lite id formats

    node_data = modify_ids(node_data, lang=lang)

    # Save node_data to disk

    with open(path, "w") as f:
        ujson.dump(node_data, f)


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
    'translatedYoutubeLang',
    'youtubeId'
]


def retrieve_kalite_data(lang="en", force=False) -> list:
    """
    Retrieve the KA content data direct from KA.
    """
    url = "http://www.khanacademy.org/api/v2/topics/topictree?lang={lang}&projection={projection}"

    projection = OrderedDict([
        ("topics", [OrderedDict((key, 1) for key in topic_attributes)]),
        ("exercises", [OrderedDict((key, 1) for key in exercise_attributes)]),
        ("videos", [OrderedDict((key, 1) for key in video_attributes)])
    ])

    url = url.format(projection=json.dumps(projection), lang=lang)
    
    node_data_path = download_and_clean_kalite_data(url, lang=lang, ignorecache=force, filename="nodes.json")

    with open(node_data_path, 'r') as f:
        node_data = ujson.load(f)

    # node_data = addin_dubbed_video_mappings(node_data, lang) 

    return node_data


def addin_dubbed_video_mappings(node_data, lang="en"):
    # Get the dubbed videos from the spreadsheet and substitute them 
    # for the video attributes of the returned data struct.
    lang_name = get_lang_name(lang).lower()

    dubbed_videos_path = pkgutil.get_data('contentpacks', "resources/dubbed_video_mappings.json")
    dubbed_videos_load = ujson.loads(dubbed_videos_path)
    dubbed_videos_list = dubbed_videos_load[lang_name]

    node_data_list = []
    for obj in node_data:
        if (obj["kind"] == "Video"):
            node_data_list.append(obj["youtube_id"])

    en_nodes_list = []
    en_nodes = pkgutil.get_data('contentpacks', "resources/en-nodes.json")
    en_node_load = ujson.loads(en_nodes)
    for node in en_node_load:
        if (node["kind"] == "Video"):
            if not node["youtube_id"] in node_data_list:
                if node["youtube_id"] in dubbed_videos_list:
                    node["youtube_id"] = dubbed_videos_list[node["youtube_id"]]
                    node["translated_youtube_lang"] = lang
                    en_nodes_list.append(node)

    node_data += en_nodes_list

    return node_data


def clean_assessment_item(assessment_item) -> dict:
    item = {}
    for key, val in assessment_item.items():
        if key in AssessmentItem._meta.get_field_names():
            item[key] = val
    return item


@cache_file
def download_assessment_item_data(url, path, lang=None, force=False) -> str:
    """
    Retrieve assessment item data and save to disk
    :param url: url of assessment item
    :param lang: language to retrieve data in
    :param force: refetch assessment item and images even if it exists on disk
    :return: path to assessment item file
    """
    attempts = 1
    logging.info("Downloading assessment item data from {url}, attempt {attempts}".format(url=url, attempts=attempts))
    data = requests.get(url)
    while data.status_code != 200 and attempts <= 5:
        logging.info(
            "Downloading assessment item data from {url}, attempt {attempts}".format(url=url, attempts=attempts))
        data = requests.get(url)
        attempts += 1

    if data.status_code != 200:
        raise requests.RequestException

    item_data = ujson.loads(data.content)

    item_data = clean_assessment_item(item_data)

    with open(path, 'w') as f:
        json.dump(item_data, f)
        f.flush()


def _get_path_from_filename(filename):
    return "/content/assessment/khan/" + _get_subpath_from_filename(filename)


def _get_subpath_from_filename(filename):
    filename = filename.replace("%20", "_")
    return "%s/%s" % (filename[0:3], filename)


def _old_image_url_to_content_url(matchobj):
    url = matchobj.group(0)
    if url in IMAGE_URLS_NOT_TO_REPLACE:
        return url
    return _get_path_from_filename(matchobj.group("filename"))


def _old_graphie_url_to_content_url(matchobj):
    return "web+graphie:" + _get_path_from_filename(matchobj.group("filename"))


IMAGE_URL_REGEX = re.compile('https?://[\w\.\-\/]+\/(?P<filename>[\w\.\-%]+\.(png|gif|jpg|jpeg|svg))',
                             flags=re.IGNORECASE)

WEB_GRAPHIE_URL_REGEX = re.compile('web\+graphie://ka\-perseus\-graphie\.s3\.amazonaws\.com\/(?P<filename>\w+)',
                                   flags=re.IGNORECASE)

IMAGE_URLS_NOT_TO_REPLACE = {"http://www.dogs.com/photo.jpg",
                             "https://www.kasandbox.org/programming-images/creatures/OhNoes.png"}

# This is used for image URLs that don't end in an image extension, or are otherwise messed up.
# Here we can manually map such URLs to a nice, friendly filename that will get used in the assessment item data.
MANUAL_IMAGE_URL_TO_FILENAME_MAPPING = {
    "http://www.marineland.com/~/media/UPG/Marineland/Products/Glass%20Aquariums/Cube%20Aquariums/12268%20MCT45B%200509jpg49110640x640.ashx?w=300&h=300&bc=white": "aquarium.jpg",
    "https://encrypted-tbn1.gstatic.com/images?q=tbn:ANd9GcSbTT6DecPnyTp5t-Ar9bgQcwNxLV8F6dvSFDYHKZSs1JINCCRFJw": "ar9bgqcwnxlv8f6dvsfdyhkzss1jinccrfjw.jpg",
}

# this ugly regex looks for links to content on the KA site, also including the markdown link text and surrounding bold markers (*), e.g.
# **[Read this essay to review](https://www.khanacademy.org/humanities/art-history/art-history-400-1300-medieval---byzantine-eras/anglo-saxon-england/a/the-lindisfarne-gospels)**
# TODO(jamalex): answer any questions people might have when this breaks!
CONTENT_URL_REGEX_PLAIN = "https?://www\.khanacademy\.org/[\/\w\-\%]*/./(?P<slug>[\w\-]+)"
CONTENT_URL_REGEX = re.compile("(?P<prefix>)" + CONTENT_URL_REGEX_PLAIN + "(?P<suffix>)", flags=re.IGNORECASE)
CONTENT_LINK_REGEX = re.compile("(?P<prefix>\**\[[^\]\[]+\] ?\(?) ?" + CONTENT_URL_REGEX_PLAIN + "(?P<suffix>\)? ?\**)",
                                flags=re.IGNORECASE)


def localize_image_urls(item):
    for url, filename in MANUAL_IMAGE_URL_TO_FILENAME_MAPPING.items():
        item["item_data"] = item["item_data"].replace(url, _get_path_from_filename(filename))
    item["item_data"] = re.sub(IMAGE_URL_REGEX, _old_image_url_to_content_url, item["item_data"])
    return item


def find_all_image_urls(item):
    for url in MANUAL_IMAGE_URL_TO_FILENAME_MAPPING:
        if url in item["item_data"]:
            yield url

    for match in re.finditer(IMAGE_URL_REGEX, item["item_data"]):
        if match.group(0) not in IMAGE_URLS_NOT_TO_REPLACE:
            yield str(match.group(0))  # match.group(0) means get the entire string


def find_all_graphie_urls(item):
    for match in re.finditer(WEB_GRAPHIE_URL_REGEX, item["item_data"]):
        base_filename = str(match.group(0)).replace("web+graphie:",
                                                    "https:")  # match.group(0) means get the entire string
        yield base_filename + ".svg"
        yield base_filename + "-data.json"


def localize_graphie_urls(item):
    item["item_data"] = re.sub(WEB_GRAPHIE_URL_REGEX, _old_graphie_url_to_content_url, item["item_data"])
    return item


def localize_content_links(item):
    item["item_data"] = re.sub(CONTENT_LINK_REGEX, _old_content_links_to_local_links, item["item_data"])
    item["item_data"] = re.sub(CONTENT_URL_REGEX, _old_content_links_to_local_links, item["item_data"])
    return item


def _old_content_links_to_local_links(matchobj):
    # replace links in them to point to local resources, if available, otherwise return an empty string
    content = _get_content_by_readable_id(matchobj.group("slug"))
    url = matchobj.group(0)
    if not content or "path" not in content:
        if "/a/" not in url and "/p/" not in url:
            logging.debug("Content link target not found:", url)
        return ""

    return "%s/learn/%s%s" % (matchobj.group("prefix"), content["path"], matchobj.group("suffix"))


CONTENT_BY_READABLE_ID = None


def _get_content_by_readable_id(readable_id):
    global CONTENT_BY_READABLE_ID
    if not CONTENT_BY_READABLE_ID:
        CONTENT_BY_READABLE_ID = dict(
            [(c.get("readable_id"), c) for c in retrieve_kalite_data() if c.get("readable_id")])
    try:
        return CONTENT_BY_READABLE_ID[readable_id]
    except KeyError:
        return CONTENT_BY_READABLE_ID.get(re.sub("\-+", "-", readable_id).lower())


def retrieve_assessment_item_data(assessment_item, lang=None, force=False, no_item_data=False, no_item_resources=False) -> (dict, [str]):
    """
    Retrieve assessment item data and images for a single assessment item.
    :param assessment_item: id of assessment item
    :param lang: language to retrieve data in
    :param force: refetch assessment item and images even if it exists on disk
    :return: tuple of dict of assessment item data and list of paths to files
    """
    if no_item_data:
        return {}, []

    if lang:
        url = "http://www.khanacademy.org/api/v1/assessment_items/{assessment_item}?lang={lang}".format(lang=lang, assessment_item=assessment_item)
        filename = "assessment_items/{assessment_item}_{lang}.json".format(lang=lang, assessment_item=assessment_item)
    else:
        url = "http://www.khanacademy.org/api/v1/assessment_items/{assessment_item}"
        filename = "assessment_items/{assessment_item}.json"
    try:
        url = url.format(assessment_item=assessment_item)
        filename = filename.format(assessment_item=assessment_item)
        path = download_assessment_item_data(url, filename=filename, lang=lang, force=force)
    except requests.RequestException:
        logging.error("Download failure for assessment item: {assessment_item}".format(assessment_item=assessment_item))
        raise

    with open(path, "r") as f:
        item_data = json.load(f)

    image_urls = find_all_image_urls(item_data)
    graphie_urls = find_all_graphie_urls(item_data)
    urls = list(itertools.chain(image_urls, graphie_urls))

    def _download_image_urls(url):
        filename = MANUAL_IMAGE_URL_TO_FILENAME_MAPPING.get(url, os.path.basename(url))
        filepath = _get_subpath_from_filename(filename)
        return download_and_cache_file(url, filename=filepath)

    file_paths = [] if no_item_resources else list(map(_download_image_urls, urls))

    item_data = localize_image_urls(item_data)
    item_data = localize_content_links(item_data)
    item_data = localize_graphie_urls(item_data)

    return item_data, file_paths


def retrieve_all_assessment_item_data(lang=None, force=False, node_data=None, no_item_data=False, no_item_resources=False) -> ([dict], set):
    """
    Retrieve Khan Academy assessment items and associated images from KA.
    :param lang: language to retrieve data in
    :param force: refetch all assessment items
    :param node_data: list of dicts containing node data to collect assessment items for
    :return: a tuple of a list of assessment item data dicts, and a list of filepaths for the zip file
    """
    if not node_data:
        node_data = retrieve_kalite_data(lang=lang)

    pool = ThreadPool()

    def _download_item_data_and_files(assessment_item):
        item_id = assessment_item.get("id")
        try:
            item_data, file_paths = retrieve_assessment_item_data(item_id, lang=lang, force=force, no_item_data=no_item_data, no_item_resources=no_item_resources)
            return item_data, file_paths
        except requests.RequestException as e:
            logging.warning("got requests exception: {}".format(e))
            return {}, []
        except json.JSONDecodeError:
            logging.warning("got a JSONDecodeError for {}".format(item_id))
            return {}, []
        except urllib.error.HTTPError as e:
            logging.warning("querying assessment item {} got an error: ".format(item_id, e))
            return {}, []

    # Unique list of assessment_items
    assessment_items = {}
    for node in node_data:
        for assessment_item in node.get("all_assessment_items", []):
            assessment_items[assessment_item.get("id")] = assessment_item

    assessment_items = assessment_items.values()

    logging.info("Retrieving assessment item data for all assessment items.")
    data_and_files = pool.map(_download_item_data_and_files, assessment_items)
    try:
        assessment_item_data, all_file_paths = zip(*data_and_files)
    except ValueError:
        logging.warning("No assessment iitems fetched at all.")
        return [], set()

    # remove empty assessment_item_data
    assessment_item_data = (data for data in assessment_item_data if data)

    # all_file_paths is a list of lists, so we need to flatten it first before deduping through set()
    all_file_paths = itertools.chain.from_iterable(all_file_paths)

    return assessment_item_data, set(all_file_paths)


def query_remote_content_file_sizes(content_items, threads=NUM_PROCESSES):
    """
    Query and store the file sizes for downloadable videos, by running HEAD requests against them,
    and reading the `content-length` header. Right now, this is only for the "khan" channel, and hence lives here.
    TODO(jamalex): Generalize this to other channels once they're centrally hosted and downloadable.
    """

    sizes_by_id = {}

    if isinstance(content_items, dict):
        content_items = content_items.values()

    content_items = [content for content in content_items if content.get("format") in content.get("download_urls", {}) and content.get("youtube_id")]

    pool = ThreadPool(threads)
    sizes = pool.map(get_content_length, content_items)

    for content, size in zip(content_items, sizes):
        # TODO(jamalex): This should be generalized from "youtube_id" to support other content types
        if size:
            sizes_by_id[content["youtube_id"]] = size

    return sizes_by_id


def get_content_length(content):
    url = content["download_urls"][content["format"]].replace("http://fastly.kastatic.org/", "http://s3.amazonaws.com/") # because fastly is SLOWLY
    logging.info("Checking remote file size for content '{title}' at {url}...".format(title=content.get("title"), url=url))
    size = 0
    for i in range(5):
        try:
            size = int(requests.head(url, timeout=60).headers["content-length"])
            break
        except requests.Timeout:
            logging.warning("Timed out on try {i} while checking remote file size for '{title}'!".format(title=content.get("title"), i=i))
        except requests.ConnectionError:
            logging.warning("Connection error on try {i} while checking remote file size for '{title}'!".format(title=content.get("title"), i=i))
        except TypeError:
            logging.warning("No numeric content-length returned while checking remote file size for '{title}' ({readable_id})!".format(**content))
            break
    if size:
        logging.info("Finished checking remote file size for content '{title}'!".format(title=content.get("title")))
    else:
        logging.error("No file size retrieved (timeouts?) for content '{title}'!".format(title=content.get("title")))
    return size


def apply_dubbed_video_map(content_data: list, subtitles: list, lang: str) -> (list, int):

    if lang != "en":

        dubbed_content = []

        dubbed_count = 0

        for item in content_data:
            if item["kind"] == NodeType.video:
                if is_video_node_dubbed(item, lang):
                    dubbed_count += 1
                elif item["youtube_id"] not in subtitles:
                    continue
            dubbed_content.append(item)

        content_data = dubbed_content

    else:
        dubbed_count = sum(content_datum.get("kind") == NodeType.video for content_datum in content_data)

    for item in content_data:
        item["remote_size"] = item.pop("download_size", 0)
        if item["remote_size"]:
            item["total_files"] = 1


    print(">>>>>>>>>>>>content-data",  content_data)

    return content_data, dubbed_count

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
        except requests.exceptions.HTTPError as e:
            logging.warning("Failed to fetch html for exercise {}, exception: {}".format(exercise_id, e))
            return None

    pool = ThreadPool(processes=NUM_PROCESSES)
    translated_exercises = pool.map(_download_html_exercise, exercises)
    # filter out Nones, since it means we got an error downloading those exercises
    result = [e for e in translated_exercises if e]
    return (BUILD_DIR, result)

def _list_all_exercises_with_bad_links():
    """This is a standalone helper method used to provide KA with a list of exercises with bad URLs in them."""
    url_pattern = r"https?://www\.khanacademy\.org/[\/\w\-]*/./(?P<slug>[\w\-]+)"
    assessment_items = {item.get("id"): item for item in retrieve_all_assessment_item_data()}
    for ex in retrieve_kalite_data():
        if ex.get("kind") == "Exercise":
            checked_urls = []
            displayed_title = False
            for aidict in ex.get("all_assessment_items", []):
                ai = assessment_items[aidict["id"]]
                for match in re.finditer(url_pattern, ai["item_data"], flags=re.IGNORECASE):
                    url = str(match.group(0))
                    if url in checked_urls:
                        continue
                    checked_urls.append(url)
                    status_code = requests.get(url).status_code
                    if status_code != 200:
                        if not displayed_title:
                            logging.debug("bad link for exercise: '%s'" % ex["title"], ex["path"])
                            displayed_title = True
