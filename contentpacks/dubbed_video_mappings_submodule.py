import errno
import os
import logging
import json
# from fle_utils.general import softload_json

CACHE_VARS = []
TOPICS_DATA_PATH = os.path.realpath(os.path.dirname(os.path.realpath(__file__))) + "/"
TOPICS_FILEPATH = os.path.join(TOPICS_DATA_PATH + "resources", "topics.json")


def softload_json(json_filepath, default={}, raises=False, logger=None, errmsg="Failed to read json file"):
    if default == {}:
        default = {}
    try:
        with open(json_filepath, "r") as fp:
            return json.load(fp)
    except Exception as e:
        if logger:
            logger("%s %s: %s" % (errmsg, json_filepath, e))
        if raises:
            raise
        return default

# Globals that can be filled
TOPICS          = None
CACHE_VARS.append("TOPICS")
def get_topic_tree(force=False, props=None):
    global TOPICS, TOPICS_FILEPATH
    if TOPICS is None or force:
        TOPICS = softload_json(TOPICS_FILEPATH, logger=logging.debug, raises=True)
        validate_ancestor_ids(TOPICS)  # make sure ancestor_ids are set properly

        # Limit the memory footprint by unloading particular values
        if props:
            node_cache = get_node_cache()
            for kind, list_by_kind in node_cache.iteritems():
                for node_list in list_by_kind.values():
                    for node in node_list:
                        for att in node.keys():
                            if att not in props:
                                del node[att]
    return TOPICS

def validate_ancestor_ids(topictree=None):
    """
    Given the KA Lite topic tree, make sure all parent_id and ancestor_ids are stamped
    """

    if not topictree:
        topictree = get_topic_tree()

    def recurse_nodes(node, ancestor_ids=[]):
        # Add ancestor properties
        if not "parent_id" in node:
            node["parent_id"] = ancestor_ids[-1] if ancestor_ids else None
        if not "ancestor_ids" in node:
            node["ancestor_ids"] = ancestor_ids

        # Do the recursion
        for child in node.get("children", []):
            recurse_nodes(child, ancestor_ids=ancestor_ids + [node["id"]])
    recurse_nodes(topictree)

    return topictree

NODE_CACHE = None
CACHE_VARS.append("NODE_CACHE")
def get_node_cache(node_type=None, force=False):
    global NODE_CACHE
    if NODE_CACHE is None or force:
        NODE_CACHE = generate_node_cache(get_topic_tree(force))
    if node_type is None:
        return NODE_CACHE
    else:
        return NODE_CACHE[node_type]

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


def generate_node_cache(topictree=None):
    """
    Given the KA Lite topic tree, generate a dictionary of all Topic, Exercise, and Video nodes.
    """

    if not topictree:
        topictree = get_topic_tree()
    node_cache = {}


    def recurse_nodes(node):
        # Add the node to the node cache
        kind = node["kind"]
        node_cache[kind] = node_cache.get(kind, {})

        if node["id"] not in node_cache[kind]:
            node_cache[kind][node["id"]] = []
        node_cache[kind][node["id"]] += [node]        # Append

        # Do the recursion
        for child in node.get("children", []):
            recurse_nodes(child)
    recurse_nodes(topictree)

    return node_cache
