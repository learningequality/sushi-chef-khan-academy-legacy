import i18nhelpers
import pytest




def test_download_and_return_content():
  assert type(i18nhelpers.retrieve_kalite_content_data()) == dict

def test_download_and_return_exercise():
  assert type(i18nhelpers.retrieve_kalite_exercise_data()) == dict

def test_download_and_return_topic():
  assert type(i18nhelpers.retrieve_kalite_topic_data()) == dict


"""
def test_subtitles():
  subtitles = i18nhelpers.retrieve_kalite_subtitles()
  assert type(subtitles) == list
  assert isinstance(subtitles[0],str)
"""







# return a list of subtitle file names