Learning Equality Content pack maker
=================================

Requirements:
-------
- Python 3.5

To start development:
-------

#### Create a virtual environment “content-pack” that you will work in:

- > `sudo pip install virtualenvwrapper`
- > `mkvirtualenv content-pack`
- > `workon content-pack`

#### Install additional development tools:

- > pip install -r requirements.txt
- > pip install -r requirements_dev.txt

#### To create language packs:

- Run `make langpacks` from the project root directory.
- Language packs located at `/out/langpacks/*.zip`

To run all tests, do a `py.test` from the project's root directory.