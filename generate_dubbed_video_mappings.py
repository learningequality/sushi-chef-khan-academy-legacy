#!/usr/bin/python

import re
import logging
import requests
import os
import csv
from StringIO import StringIO
import sys, getopt
import json


from contentpacks.dubbed_video_mappings_submodule import ensure_dir, get_node_cache
from khan_api_python.api_models import Khan

PROJECT_PATH = os.path.realpath(os.path.dirname(os.path.realpath(__file__))) + "/"

CACHE_FILEPATH = os.path.join(PROJECT_PATH + "build/csv", 'khan_dubbed_videos.csv')
DUBBED_LANGUAGES_FETCHED_IN_API = ["es", "fr"]


def dubbed_video_data_from_api(lang_code):
    k = Khan(lang="en")
    videos = k.get_videos()
    return {v["youtube_id"]: v["translated_youtube_id"] for v in videos if v["youtube_id"] != v["translated_youtube_id"]}

# TODO (arceduardvincent): Remove the CACHE_FILEPATH and replace it to None when done mapping the source code.
def download_ka_dubbed_video_csv(download_url=None, cache_filepath=None):
    download_url = "https://docs.google.com/spreadsheets/d/1k5xh2UXV3EchRHnYzeP6-YGKrmba22vsltGSuU9bL88/export?format=csv&id=1k5xh2UXV3EchRHnYzeP6-YGKrmba22vsltGSuU9bL88&gid=0"

    # response = requests.get(download_url)
    # if response.history:
    #     print "Request was redirected"
    #     for resp in response.history:
    #         print resp.status_code, resp.url
    #         download_url = resp.url
    #     print "Final destination:"
    #     print response.status_code, response.url
    # else:
    #     print "Request was not redirected"
    #
    logging.info("Downloading dubbed video data from %s" % download_url)
    response = requests.get(download_url)
    if response.status_code != 200:
        logging.warning("Failed to download dubbed video CSV data: status=%s" % response.status)
    csv_data = response.content

    # Dump the data to a local cache file
    try:
        ensure_dir(os.path.dirname(cache_filepath))
        with open(cache_filepath, "w") as fp:
            fp.write(csv_data)
    except Exception as e:
        logging.error("Failed to make a local cache of the CSV data: %s; parsing local data" % e)

    return csv_data

def generate_dubbed_video_mappings_from_csv(csv_data=None):

    # This CSV file is in standard format: separated by ",", quoted by '"'
    logging.info("Parsing csv file.")
    reader = csv.reader(StringIO(csv_data))

    # Build a two-level video map.
    #   First key: language name
    #   Second key: english youtube ID
    #   Value: corresponding youtube ID in the new language.
    video_map = {}

    # Loop through each row in the spreadsheet.
    for row in reader:
        # skip over the header rows
        if row[0].strip() in ["", "UPDATED:"]:
            continue

        elif row[0] == "SERIAL":
            # Read the header row.
            header_row = [v.lower() for v in row]  # lcase all header row values (including language names)
            slug_idx = header_row.index("title id")
            english_idx = header_row.index("english")
            assert slug_idx != -1, "Video slug column header should be found."
            assert english_idx != -1, "English video column header should be found."

        else:
            # Rows 6 and beyond are data.
            assert len(row) == len(header_row), "Values line length equals headers line length"

            # Grab the slug and english video ID.
            video_slug = row[slug_idx]
            english_video_id = row[english_idx]
            assert english_video_id, "English Video ID should not be empty"
            assert video_slug, "Slug should not be empty"

            # English video is the first video ID column,
            #   and following columns (until the end) are other languages.
            # Loop through those columns and, if a video exists,
            #   add it to the dictionary.
            for idx in range(english_idx, len(row)):
                if not row[idx]:  # make sure there's a dubbed video
                    continue

                lang = header_row[idx]
                if lang not in video_map:  # add the first level if it doesn't exist
                    video_map[lang] = {}
                dubbed_youtube_id = row[idx]
                if english_video_id == dubbed_youtube_id and lang != "english":
                    logging.error("Removing entry for (%s, %s): dubbed and english youtube ID are the same." % (lang, english_video_id))
                #elif dubbed_youtube_id in video_map[lang].values():
                    # Talked to Bilal, and this is actually supposed to be OK.  Would throw us for a loop!
                    #    For now, just keep one.
                    #for key in video_map[lang].keys():
                    #    if video_map[lang][key] == dubbed_youtube_id:
                    #        del video_map[lang][key]
                    #        break
                    #logging.error("Removing entry for (%s, %s): the same dubbed video ID is used in two places, and we can only keep one in our current system." % (lang, english_video_id))
                else:
                    video_map[lang][english_video_id] = row[idx]  # add the corresponding video id for the video, in this language.

    # Now, validate the mappings with our topic data
    known_videos = get_node_cache("Video").keys()
    missing_videos = set(known_videos) - set(video_map["english"].keys())
    extra_videos = set(video_map["english"].keys()) - set(known_videos)
    if missing_videos:
        logging.warn("There are %d known videos not in the list of dubbed videos" % len(missing_videos))
        logging.warn("Adding missing English videos to English dubbed video map")
        for video in missing_videos:
            video_map["english"][video] = video
    if extra_videos:
        logging.warn("There are %d videos in the list of dubbed videos that we have never heard of." % len(extra_videos))

    return video_map

DUBBED_VIDEOS_MAPPING_FILEPATH = os.path.join(PROJECT_PATH + "build/csv",  "dubbed_video_mappings.json")


def main(argv):
    # old_map = os.path.exists(DUBBED_VIDEOS_MAPPING_FILEPATH) and copy.deepcopy(get_dubbed_video_map()) or {}  # for comparison purposes
    csv_data = download_ka_dubbed_video_csv(cache_filepath=CACHE_FILEPATH)
    max_cache_age = 0.0
    raw_map = generate_dubbed_video_mappings_from_csv(csv_data=csv_data)


    # Remove any dummy (empty) entries, as this breaks everything on the client
    # if "" in raw_map:
    #     del raw_map[""]
    #
    # for lang_code in DUBBED_LANGUAGES_FETCHED_IN_API:
    #     logging.info("Updating {} from the API".format(lang_code))
    #     map_from_api = dubbed_video_data_from_api(lang_code)
    #     lang_metadata = get_code2lang_map(lang_code)
    #     lang_ka_name = lang_metadata["ka_name"]
    #     raw_map[lang_ka_name].update(map_from_api)

    # # Now we've built the map.  Save it.
    # ensure_dir(os.path.dirname(DUBBED_VIDEOS_MAPPING_FILEPATH))
    # logging.info("Saving data to %s" % DUBBED_VIDEOS_MAPPING_FILEPATH)
    # with open(DUBBED_VIDEOS_MAPPING_FILEPATH, "w") as fp:
    #     json.dump(raw_map, fp)
    #
    # new_map = get_dubbed_video_map(reload=True)
    #
    # # Now tell the user about what changed.
    # added_languages = set(new_map.keys()) - set(old_map.keys())
    # removed_languages = set(old_map.keys()) - set(new_map.keys())
    # if added_languages or removed_languages:
    #     logging.info("*** Added support for %2d languages; removed support for %2d languages. ***" % (
    #     len(added_languages), len(removed_languages)))
    #
    # for lang_code in sorted(list(set(new_map.keys()).union(set(old_map.keys())))):
    #     added_videos = set(new_map.get(lang_code, {}).keys()) - set(old_map.get(lang_code, {}).keys())
    #     removed_videos = set(old_map.get(lang_code, {}).keys()) - set(new_map.get(lang_code, {}).keys())
    #     shared_keys = set(new_map.get(lang_code, {}).keys()).intersection(set(old_map.get(lang_code, {}).keys()))
    #     changed_videos = [vid for vid in shared_keys if
    #                       old_map.get(lang_code, {})[vid] != new_map.get(lang_code, {})[vid]]
    #     logging.info("\t%5s: Added %d videos, removed %3d videos, changed %3d videos." % (
    #     lang_code, len(added_videos), len(removed_videos), len(changed_videos)))

    # logging.info("Done.")

   # try:
   #    opts, args = getopt.getopt(argv,"hi:o:",["ifile=","ofile="])
   # except getopt.GetoptError:
   #    print 'generate_dubbed_video_mappings.py -i <inputfile> -o <outputfile>'
   #    sys.exit(2)
   #
   # for opt, arg in opts:
   #    if opt == '-h':
   #       print 'generate_dubbed_video_mappings.py -i <inputfile> -o <outputfile>'
   #       sys.exit()
   #    elif opt in ("-i", "--ifile"):
   #       inputfile = arg
   #    elif opt in ("-o", "--ofile"):
   #       outputfile = arg
   #
   # print 'Input file is "', inputfile
   # print 'Output file is "', outputfile


if __name__ == "__main__":
   main(sys.argv[1:])