
import csv
import errno
import getopt
import json
import logging
import os
import requests
import sys
import urllib

from io import StringIO


PROJECT_PATH = os.path.join(os.getcwd())
CACHE_FILEPATH = os.path.join(PROJECT_PATH, "build", "csv", 'khan_dubbed_videos.csv')
DUBBED_VIDEOS_MAPPING_FILEPATH = os.path.join(PROJECT_PATH, "build",  "dubbed_video_mappings.json")

logging.getLogger().setLevel(logging.INFO)


# http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python
def ensure_dir(path):
    """Create the entire directory path, if it doesn't exist already."""
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST:
            # file already exists
            if not os.path.isdir(path):
                # file exists but is not a directory
                raise OSError(errno.ENOTDIR, "Not a directory: '%s'" % path)
            pass  # directory already exists
        else:
            raise


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

    data = requests.get(download_url)
    attempts = 1
    while data.status_code != 200 and attempts <= 100:
        time.sleep(30)
        data = requests.get(url)
        attempts += 1

    if data.status_code != 200:
        raise requests.RequestException("Failed to download dubbed video CSV data: %s" % data.content)
    csv_data = data.content

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
    return video_map


def main():
    input_csv_file = False
    try:
       opts, args = getopt.getopt([],"hc:o:",["csvfile=","ofile="])
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