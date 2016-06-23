"""
generate_en_nodes

Create en_nodes.json file to be used in dubbed video mappings.

Usage:
  generate_en_nodes.py
"""

import json
import shutil
import os

from collections import OrderedDict
from contentpacks.khanacademy import retrieve_kalite_data

PROJECT_PATH = os.path.realpath(os.path.dirname(os.path.realpath(__file__)))
EN_NODE_PATH = os.path.join(PROJECT_PATH, "build", 'en_nodes.json')
RESOURCES_PATH = os.path.join(PROJECT_PATH, "contentpacks", "resources")


def main():
    """
    This will generate en_nodes.json file that will be used in dubbed video mappings.
    """
    lang = "en"
    name = "en_nodes.json"
    retrieve_kalite_data(lang, force=False, filename=name)

    # Copy en_nodes.json to contentpacks resources.
    try:
        shutil.copy2(EN_NODE_PATH, RESOURCES_PATH)
    except:
       logging.warn('Error copying en_node.json to contentpacks resources')


if __name__ == "__main__":
    main()