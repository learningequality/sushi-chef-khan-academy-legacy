#!/usr/bin/env python3
from le_utils.constants.languages import getlang
from html2text import html2text
from le_utils.constants import licenses
from ricecooker.chefs import SushiChef
from ricecooker.classes.nodes import (ChannelNode, ExerciseNode, VideoNode, TopicNode)
from ricecooker.classes.questions import PerseusQuestion
from ricecooker.classes.files import VideoFile, YouTubeSubtitleFile
import subprocess
import re
import os
import pickle
import requests
import copy

FILE_URL_REGEX = re.compile('[\\\]*/content[\\\]*/assessment[\\\]*/khan[\\\]*/(?P<build_path>\w+)[\\\]*/(?P<filename>\w+)\.?(?P<ext>\w+)?', flags=re.IGNORECASE)
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


# utility function to remove topic nodes with no content under them
def clean_nodes(node):
    copy_children = copy.copy(node.children)
    for child in copy_children:
        if not child.children and child.kind == 'topic':
            node.children.remove(child)
        else:
            idx = node.children.index(child)
            clean_nodes(node.children[idx])
    if not node.children and node.kind == 'topic':
        node.parent.children.remove(node)

class KASushiChef(SushiChef):

    def get_channel(self, *args, **kwargs):

        lang_code = kwargs['lang']

        channel = ChannelNode(
            source_id="KA ({0})".format(lang_code),
            source_domain="khanacademy.org",
            title="Khan Academy ({0})".format(lang_code),
            description='Khan Academy content for the {0} language.'.format(lang_code),
            thumbnail="https://cdn.kastatic.org/images/khan-logo-vertical-transparent.png",
        )

        return channel


    def construct_channel(self, *args, **kwargs):

        channel = self.get_channel(*args, **kwargs)
        lang = kwargs['lang']
        subprocess.run('make {0}'.format(lang), shell=True, check=True)

        with open('node_data_{0}.pickle'.format(lang), 'rb') as handle:
            node_data = pickle.load(handle)

        with open('assessment_data_{0}.pickle'.format(lang), 'rb') as handle:
            assessment_data = pickle.load(handle)

        # create mapping between ids and each assessment item
        assessment_dict = {}
        for item in assessment_data:
            assessment_dict[item['id']] = item

        tree = _build_tree(channel, node_data, assessment_dict, lang)
        clean_nodes(tree)

        return tree


def _build_tree(channel, node_data, assessment_dict, lang_code):

    # recall KA api for exercises dict
    ka_exercises = requests.get('http://www.khanacademy.org/api/v1/exercises').json()
    mapping = {}
    for item in ka_exercises:
        mapping[item['node_slug'].split('/')[-1]] = item

    # adds mastery models and exercise thumbnails
    for idx in range(len(node_data)):
        if node_data[idx].get('kind') == 'Exercise':
            if node_data[idx].get('id') in mapping:
                copy = node_data[idx]
                copy['image_url_256'] = mapping[node_data[idx].get('id')]['image_url_256']
                copy['suggested_completion_criteria'] = mapping[node_data[idx].get('id')]['suggested_completion_criteria']
                node_data[idx] = copy

    # get correct base url
    if lang_code != 'en':
        base_path = 'https://{}.khanacademy.org'.format(lang_code.lower())
    else:
        base_path = 'https://www.khanacademy.org'

    # if not lite version in page content, add previews to questions
    lite_version = 'format=lite' in requests.get(base_path)

    channel.path = 'khan'
    node_data.pop(0)

    for node in node_data:
        paths = node['path'].split('/')[:-1]
        # recurse tree structure based on paths of node
        parent = _getNode(paths, channel)
        # nodes with no parents are being returned by content pack maker, hence this check
        if parent is None:
            continue
        child_node = create_node(node, assessment_dict, base_path, lite_version, lang_code)  # create node based on kinds
        if child_node and child_node not in parent.children:
            child_node.path = paths[-1]
            parent.add_child(child_node)

    return channel


def create_node(node, assessment_dict, base_path, lite_version, lang_code):

    kind = node.get('kind')
    # Exercise node creation
    if kind == 'Exercise':
        child_node = ExerciseNode(
            source_id=node['id'],
            title=node['title'],
            exercise_data={'mastery_model': node.get('suggested_completion_criteria')},
            description='' if node.get("description") is None else node.get("description", '')[:400],
            license=licenses.ALL_RIGHTS_RESERVED,
            thumbnail=node.get('image_url_256'),
        )

        # build exercise urls for previews
        full_path = base_path + node.get('path').strip('khan')
        slug = full_path.split('/')[-2]
        full_path = full_path.replace(slug, 'e') + slug

        # attach Perseus questions to Exercises
        for item in node['all_assessment_items']:
            # we replace all references to assessment images with the local file path to the image
            for match in re.finditer(FILE_URL_REGEX, assessment_dict[item['id']]["item_data"]):
                file_path = str(match.group(0)).replace('\\', '')
                file_path = file_path.replace(REPLACE_STRING, IMAGE_DL_LOCATION)
                assessment_dict[item['id']]["item_data"] = re.sub(FILE_URL_REGEX, file_path, assessment_dict[item['id']]["item_data"], 1)
            question = PerseusQuestion(
                id=item['id'],
                raw_data=assessment_dict[item['id']]['item_data'],
                source_url=full_path if not lite_version else None,
            )
            child_node.add_question(question)

    # Topic node creation
    elif kind == 'Topic':
        child_node = TopicNode(
            source_id=node["id"],
            title=node["title"],
            description='' if node.get("description") is None else node.get("description", '')[:400]
        )

    # Video node creation
    elif kind == 'Video':
        if node.get('description_html'):
            video_description = html2text(node.get('description_html'))[:400]
        elif node.get('description'):
            video_description = node.get('description')[:400]
        else:
            video_description = ''
        # standard download url for KA videos
        download_url = "https://cdn.kastatic.org/KA-youtube-converted/{0}.mp4/{1}.mp4".format(node['youtube_id'], node['youtube_id'])
        files = [VideoFile(download_url)]
        files.append(YouTubeSubtitleFile(node['youtube_id'], language=getlang(lang_code)))
        child_node = VideoNode(
            source_id=node["id"],
            title=node["title"],
            description=video_description,
            files=files,
            thumbnail=node.get('image_url'),
            license=licenses.CC_BY_NC_SA
        )

    else:  # unknown content file format
        return None

    return child_node

if __name__ == "__main__":
    """
    This code will run when the sushi chef is called from the command line.
    """
    chef = KASushiChef()
    chef.main()
