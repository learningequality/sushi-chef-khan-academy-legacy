Learning Equality Sushi Chef
============================

Requirements:
-------
- Python 3.5

To start development:
-------

#### Create a virtual environment “sushi-chef” that you will work in:

- > `sudo pip install virtualenvwrapper`
- > `mkvirtualenv sushi-chef`
- > `workon sushi-chef`

#### Install additional development tools:

- > pip install -r requirements.txt
- > pip install -r requirements_dev.txt
- > pip install ricecooker

#### To run sushi chef:

- > python -m ricecooker uploadchannel ka_sushi_chef.py --token={t} lang={lang_code}