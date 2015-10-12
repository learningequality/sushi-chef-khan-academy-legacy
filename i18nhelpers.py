
import collections
import os


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

    return LangpackResources(topic_data, content_data, exercise_data, subtitle_data, kalite_catalog, ka_catalog)
