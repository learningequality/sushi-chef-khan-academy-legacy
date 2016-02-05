import pytest
@pytest.fixture(scope="module")
def test_content():
    test_content= [('counting-with-small-numbers',
    {'description': 'Learn how to count squirrels and horses.',
    'download_urls': {'m3u8': 'http://fastly.kastatic.org/KA-youtube-converted/y2-uaPiyoxc.m3u8/y2-uaPiyoxc.m3u8',
                    'mp4': 'http://fastly.kastatic.org/KA-youtube-converted/y2-uaPiyoxc.mp4/y2-uaPiyoxc.mp4',
                    'png': 'http://fastly.kastatic.org/KA-youtube-converted/y2-uaPiyoxc.mp4/y2-uaPiyoxc.png'},
    'duration': 56,
    'format': 'mp4',
    'id': 'y2-uaPiyoxc',
    'keywords': '',
    'kind': 'Video',
    'path': 'khan/math/early-math/cc-early-math-counting-topic/cc-early-math-counting/counting-with-small-numbers/',
    'readable_id': 'counting-with-small-numbers',
    'slug': 'counting-with-small-numbers',
    'title': 'Counting with small numbers',
    'video_id': 'y2-uaPiyoxc',
    'youtube_id': 'y2-uaPiyoxc'})]
    
    return test_content

@pytest.fixture(scope="module")
def correct_answer():
    correct_answer = [('counting-with-small-numbers',
    {'description': 'Learn how to count squirrels and horses.',
    'download_urls': {'m3u8': 'http://fastly.kastatic.org/KA-youtube-converted/y2-uaPiyoxc.m3u8/y2-uaPiyoxc.m3u8',
                'mp4': 'http://fastly.kastatic.org/KA-youtube-converted/y2-uaPiyoxc.mp4/y2-uaPiyoxc.mp4',
                'png': 'http://fastly.kastatic.org/KA-youtube-converted/y2-uaPiyoxc.mp4/y2-uaPiyoxc.png'},
    'duration': 56,
    'format': 'mp4',
    'id': 'y2-uaPiyoxc',
    'keywords': '',
    'kind': 'Video',
    'path': 'khan/math/early-math/cc-early-math-counting-topic/cc-early-math-counting/counting-with-small-numbers/',
    'readable_id': 'counting-with-small-numbers',
    'slug': 'counting-with-small-numbers',
    'title': 'Counting with small numbers',
    'video_id': "lhS-nvcK8Co",
    'youtube_id': "lhS-nvcK8Co"})]

    return correct_answer