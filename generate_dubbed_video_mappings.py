"""
generate_dubbed_video_mappings

Create a dubbed_video_mappings.json, at contentpacks resources.

Usage:
  generate_dubbed_video_mappings.py

"""
import getopt
import logging
import requests
import os
import csv
from io import StringIO
import sys
import urllib
import json

from contentpacks.dubbed_video_mappings_submodule import ensure_dir, get_node_cache

PROJECT_PATH = os.path.realpath(os.path.dirname(os.path.realpath(__file__)))
CACHE_FILEPATH = os.path.join(PROJECT_PATH, "build", "csv", 'khan_dubbed_videos.csv')
DUBBED_VIDEOS_MAPPING_FILEPATH = os.path.join(PROJECT_PATH, "contentpacks", "resources",  "dubbed_video_mappings.json")

logging.getLogger().setLevel(logging.INFO)


def download_ka_dubbed_video_csv(download_url=None, cache_filepath=None):

    """
    Function to do the heavy lifting in getting the dubbed videos map.

    Could be moved into utils
    """
    # Get the redirect url
    if not download_url:
        logging.info("Getting spreadsheet location from Khan Academy")
        khan_url = "http://www.khanacademy.org/r/translationmapping"
        try:
            download_url = urllib.request.urlopen(khan_url).geturl()
            if "docs.google.com" not in download_url:
                logging.warn("Redirect location no longer in Google docs (%s)" % download_url)
            else:
                download_url = download_url.replace("/edit", "/export?format=csv")
        except:
            # TODO: have django email admins when we hit this exception
            raise Exception("Expected redirect response from Khan Academy redirect url.")

    logging.info("Downloading dubbed video data from %s" % download_url)
    response = requests.get(download_url)
    if response.status_code != 200:
        logging.warning("Failed to download dubbed video CSV data: status=%s" % response.status)
    csv_data = response.content

    # Dump the data to a local cache file
    csv_data = csv_data.decode("utf-8")
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

def main(argv):
    input_csv_file = False
    try:
       opts, args = getopt.getopt(argv,"hc:o:",["csvfile=","ofile="])
    except getopt.GetoptError:
       logging.warn('generate_dubbed_video_mappings.py -c <csvfile> -o <outputfile>')
       sys.exit(2)

    for opt, arg in opts:
       if opt == '-h':
          logging.info('generate_dubbed_video_mappings.py -i <csvfile> -o <outputfile>')
          sys.exit()
       elif opt in ("-c", "--csvfile"):
           csv_file = arg
           csv_data = download_ka_dubbed_video_csv(cache_filepath=csv_file)
           input_csv_file = True

       else:
          assert False, logging.info("unhandled option")

    # old_map = os.path.exists(DUBBED_VIDEOS_MAPPING_FILEPATH) and copy.deepcopy(get_dubbed_video_map()) or {}  # for comparison purposes
    if input_csv_file is False:
        csv_data = download_ka_dubbed_video_csv(cache_filepath=CACHE_FILEPATH)
    raw_map = generate_dubbed_video_mappings_from_csv(csv_data=csv_data)

    # Now we've built the map.  Save it.
    ensure_dir(os.path.dirname(DUBBED_VIDEOS_MAPPING_FILEPATH))
    logging.info("Saving data to %s" % DUBBED_VIDEOS_MAPPING_FILEPATH)
    with open(DUBBED_VIDEOS_MAPPING_FILEPATH, "w") as fp:
        json.dump(raw_map, fp)


if __name__ == "__main__":
    if os.path.exists(DUBBED_VIDEOS_MAPPING_FILEPATH):
        logging.info('Dubbed videos json %s already exist' % (DUBBED_VIDEOS_MAPPING_FILEPATH))
    else:
        main(sys.argv[1:])