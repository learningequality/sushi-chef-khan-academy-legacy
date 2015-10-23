import os
import urllib.request


def download_and_cache_file(url, cachedir=None, ignorecache=False) -> str:
    """
    Download the given url if it's not saved in cachedir. Returns the
    path to the file. Always download the file if ignorecache is True.
    """

    if not cachedir:
        cachedir = os.path.join(os.getcwd(), "build")

    os.makedirs(cachedir, exist_ok=True)

    path = os.path.join(cachedir, os.path.basename(url))

    if ignorecache or not os.path.exists(path):
        urllib.request.urlretrieve(url, path)

    return path
