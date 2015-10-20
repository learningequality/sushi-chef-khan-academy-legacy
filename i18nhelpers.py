import collections
import os
import requests
import errno
import json

CONTENT_URL = "https://raw.githubusercontent.com/learningequality/ka-lite/master/data/khan/contents.json"
EXERCISE_URL = "https://raw.githubusercontent.com/learningequality/ka-lite/master/data/khan/exercises.json"
TOPIC_URL = "https://raw.githubusercontent.com/learningequality/ka-lite/master/data/khan/topics.json"

LangpackResources = collections.namedtuple(
    "LangpackResources",
    ["topics",
     "contents",
     "exercises",
     "subtitles",
     "kalite_catalog",
     "ka_catalog"
    ])


def retrieve_language_resources(lang: str, version: str) -> LangpackResources:

    content_data = retrieve_kalite_content_data()
    exercise_data = retrieve_kalite_exercise_data()
    topic_data = retrieve_kalite_topic_data()

    subtitle_list = retrieve_subtitles(lang)

    # retrieve KA Lite po files from CrowdIn
    crowdin_project_name = "ka-lite"
    crowdin_secret_key = os.environ["KALITE_CROWDIN_SECRET_KEY"]
    includes = [version]
    kalite_catalog = retrieve_translations(crowdin_project_name, crowdin_secret_key, includes)

    # retrieve Khan Academy po files from CrowdIn
    crowdin_project_name = "khanacademy"
    crowdin_secret_key = os.environ["KA_CROWDIN_SECRET_KEY"]
    includes = [version]
    ka_catalog = retrieve_translations(crowdin_project_name, crowdin_secret_key, includes)

    return LangpackResources(topic_data, content_data, 
                            exercise_data, subtitle_data, 
                            kalite_catalog, ka_catalog)

def retrieve_kalite_topic_data():

    topic_cache = os.path.join('/tmp', 'topics.json')
    if os.path.exists(topic_cache):
        
        with open(topic_cache, 'r') as f:
            topic = json.load(f) 
        
        return topic
    else: 
        
        topic_request = requests.get(TOPIC_URL)
        with open(topic_cache, 'w') as f:
            f.write(topic_request.text)
        
        with open(topic_cache, 'r') as f:
            topic = json.load(f)
        
        return topic

def retrieve_kalite_exercise_data():
    exercise_cache = os.path.join('/tmp', 'exercises.jsons')
    if os.path.exists(exercise_cache):
        
        with open(exercise_cache, 'r') as f:
            exercise = json.load(f)
        
        return exercise
    else:
        
        exercise_request = requests.get(EXERCISE_URL)
        with open(exercise_cache, 'w') as f:
            f.write(exercise_request.text)
        
        with open(exercise_cache, 'r') as f:
            exercise = json.load(f)
        
        return exercise    

def retrieve_kalite_content_data():
    content_cache = os.path.join('/tmp', 'contents.json')
    if os.path.exists(content_cache):
        with open(content_cache, 'r') as f:
            content = json.load(f)
        return content
    else:
        
        content_request = requests.get(CONTENT_URL)
        with open(content_cache, 'w') as f:
            f.write(content_request.text)

        with open(content_cache, 'r') as  f:
            content = json.load(f)
        
        return content