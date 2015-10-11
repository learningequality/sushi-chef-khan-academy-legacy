
# topics, contents, exercises, subtitles, kalite_po_files, ka_po_files = retrieve_language_resources(lang)


import os


def retrieve_language_resources(lang, softwareversion):

    content_data = retrieve_kalite_content_data()
    exercise_data = retrieve_kalite_exercise_data()
    topic_data = retrieve_kalite_topic_data()

    subtitle_list = retrieve_subtitles(lang)

    # retrieve KA Lite po files from CrowdIn
    crowdin_project_name = "ka-lite"
    crowdin_secret_key = os.environ["KALITE_CROWDIN_SECRET_KEY"]
    includes = [softwareversion]
    kalite_catalog = retrieve_translations(crowdin_project_name, crowdin_secret_key, includes)

    # retrieve Khan Academy po files from CrowdIn
    crowdin_project_name = "khanacademy"
    crowdin_secret_key = os.environ["KA_CROWDIN_SECRET_KEY"]
    includes = [softwareversion]
    ka_catalog = retrieve_translations(crowdin_project_name, crowdin_secret_key, includes)

    return topic_data, content_data, exercise_data, kalite_catalog, ka_catalog
