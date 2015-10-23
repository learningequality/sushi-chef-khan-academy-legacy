import os
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "Content packs Maker",
    version = "0.0.1",
    author = "Learning Equality",
    author_email = "aron@learningequality.org",
    description = ("makelangpacks creates content packs usable for KA Lite/Kolibri."),
    license = "BSD",
    keywords = "contentpacks education internationalization",
    url = "https://github.com/fle-internal/content-pack-maker",
    # packages=['an_example_pypi_project', 'tests'],
    # long_description=read('README'),
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
    ],
)
