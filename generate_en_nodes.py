
import json

from collections import OrderedDict
from contentpacks.khanacademy import retrieve_kalite_data


def main():
    """
    This will generate en_nodes.json file that will be used in dubbed video mappings.
    """
    lang = "en"
    name = "en_nodes.json"
    retrieve_kalite_data(lang, force=False, filename=name)

if __name__ == "__main__":
    main()