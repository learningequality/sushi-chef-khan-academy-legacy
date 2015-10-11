"""
makepack

Usage:

"""


def make_language_pack(lang):

    topics, contents, exercises, subtitles, kalite_po_files, ka_po_files = retrieve_language_resources(lang)


    exercises = translate_exercises(exercises, ka_po_files)
    topics =  translate_topics(topics, ka_po_files)
    contents = translate_content(contents, ka_po_files)

    exercises = list(exercises)
    khan_exercises = retrieve_khan_exercises(exercises)
    perseus_items = retrieve_assessment_items(exercises)
    exercises = remove_untranslated_exercises(exercises, khan_exercises, perseus_items)

    topics = remove_unavailable_topics(topics, exercises)

    filename = "{lang}.zip".format(lang=lang)
    bundle_language_pack(filename, topics, contents, exercises, kalite_po_files, ka_po_files)
