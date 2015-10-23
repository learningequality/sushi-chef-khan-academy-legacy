"""
makepack

Usage:

"""

from i18nhelpers import retrieve_language_resources


def make_language_pack(lang):

    topic_data, content_data, exercise_data, subtitles, kalite_po_files, ka_po_files, dubmap = retrieve_language_resources(lang)


    exercise_data = translate_exercises(exercise_data, ka_po_files)
    topic_data =  translate_topics(topic_data, ka_po_files)
    content_data = translate_content(content_data, ka_po_files)

    content_data = apply_dubbed_video_map(content_data, dubmap)

    exercise_data = list(exercise_data)
    khan_exercises = retrieve_khan_exercises(exercise_data)
    perseus_items = retrieve_assessment_items(exercise_data)
    exercise_data = remove_untranslated_exercises(exercise_data, khan_exercises, perseus_items)

    # now include only the assessment item resources that we need
    all_assessment_resources = get_full_assessment_resource_list()
    included_assessment_resources = filter_unneeded_assessment_resources(all_assessment_resources, exercise_data)

    topic_data = remove_unavailable_topics(topic_data, exercise_data)

    filename = "{lang}.zip".format(lang=lang)
    bundle_language_pack(filename, topic_data, content_data, exercise_data, kalite_po_files, ka_po_files)
