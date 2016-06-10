import logging
import requests
import os
import csv
from StringIO import StringIO

from contentpacks.dubbed_video_mappings_submodule import ensure_dir, get_node_cache
from khan_api_python.api_models import Khan

PROJECT_PATH = os.path.realpath(os.path.dirname(os.path.realpath(__file__))) + "/"

CACHE_FILEPATH = os.path.join(PROJECT_PATH + "build/csv", 'khan_dubbed_videos.csv')


def dubbed_video_data_from_api(lang_code):
    k = Khan(lang="en")
    videos = k.get_videos()
    print videos
    return {v["youtube_id"]: v["translated_youtube_id"] for v in videos if v["youtube_id"] != v["translated_youtube_id"]}

# TODO (arceduardvincent): Remove the CACHE_FILEPATH and replace it to None when done mapping the source code.
def download_ka_dubbed_video_csv(download_url=None, cache_filepath=CACHE_FILEPATH):
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

download_ka_dubbed_video_csv()

def generate_dubbed_video_mappings_from_csv(csv_data=download_ka_dubbed_video_csv()):

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

generate_dubbed_video_mappings_from_csv()