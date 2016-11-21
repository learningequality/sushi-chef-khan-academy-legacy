from ricecooker.classes.nodes import (Channel, Exercise, Video, Topic)
from ricecooker.classes.questions import PerseusQuestion
import subprocess
import re
import os
import pickle

FILE_URL_REGEX = re.compile('[\\\]*/content[\\\]*/assessment[\\\]*/khan[\\\]*/(?P<build_path>\w+)[\\\]*/(?P<filename>\w+)', flags=re.IGNORECASE)
REPLACE_STRING = "/content/assessment/khan"
cwd = os.getcwd()
IMAGE_DL_LOCATION = 'file://' + cwd + '/build'


# recursive function to traverse tree and return parent node
def _getNode(paths, tree):
    for path in paths:
        if path == tree.path:
            # this means its the last node so we should return parent
            if len(paths[1:]) == 1:
                return tree
            for child in tree.children:
                parent = _getNode(paths[1:], child)
                if parent:
                    return parent
        else:  # we are not going down right path so drop out
            return None


Channel._getNode = _getNode


# temporary fix to get nodes in the correct order
def reverse_children(tree):
    tree.children = tree.children[::-1]
    for child in tree.children:
        reverse_children(child)


def construct_channel(**kwargs):

    lang = kwargs['lang']
    subprocess.run('make {0}'.format(lang), shell=True)

    with open('node_data_{0}.pickle'.format(lang), 'rb') as handle:
        node_data = pickle.load(handle)

    with open('assessment_data_{0}.pickle'.format(lang), 'rb') as handle:
        assessment_data = pickle.load(handle)

    # create mapping between ids and each assessment item
    assessment_dict = {}
    for item in assessment_data:
        assessment_dict[item['id']] = item

    tree = _build_tree(node_data, assessment_dict, lang)
    reverse_children(tree)

    return tree


def _build_tree(node_data, assessment_dict, lang_code):

    channel = Channel(
        domain="khanacademy.org",
        channel_id="abc123",
        title="Khan Academy ({0})".format(lang_code),
        thumbnail="https://cdn.kastatic.org/images/khan-logo-vertical-transparent.png",
    )
    channel.path = 'khan'
    node_data.pop(0)
    for node in node_data:
        paths = node['path'].split('/')[:-1]
        # recurse tree structure based on paths of node
        parent = _getNode(paths, channel)
        child_node = create_node(node, assessment_dict)  # create node based on kinds
        if child_node:
            child_node.path = paths[-1]
            parent.add_child(child_node)

    return channel


def create_node(node, assessment_dict):

    kind = node.get('kind')
    # Exercise node creation
    if kind == 'Exercise':
        child_node = Exercise(
            id=node['id'],
            title=node['title'],
            description=node.get('description')[:400]
        )
        # attach Perseus questions to Exercises
        for item in node['all_assessment_items']:
            for match in re.finditer(FILE_URL_REGEX, assessment_dict[item['id']]["item_data"]):
                file_path = str(match.group(0)).replace('\\', '')
                file_path = file_path.replace(REPLACE_STRING, IMAGE_DL_LOCATION)
                assessment_dict[item['id']]["item_data"] = re.sub(FILE_URL_REGEX, file_path, assessment_dict[item['id']]["item_data"], 1)
            question = PerseusQuestion(
                id=item['id'],
                raw_data=assessment_dict[item['id']]['item_data']
            )
            child_node.add_question(question)

    # Topic node creation
    elif kind == 'Topic':
        child_node = Topic(
            id=node["id"],
            title=node["title"],
            description=node.get("description")[:400]
        )

    # Video node creation
    elif kind == 'Video':
        # standard download url for KA videos
        download_url = "https://cdn.kastatic.org/KA-youtube-converted/{0}.mp4/{1}.mp4".format(node['youtube_id'], node['youtube_id'])
        child_node = Video(
            id=node["id"],
            title=node["title"],
            description=node.get("description")[:400],
            files=download_url,
            thumbnail=node.get('image_url')
        )

    else:  # unknown content file format
        return None

    return child_node
