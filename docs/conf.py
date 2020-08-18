# coding: utf-8

import datetime as dt
import os
import sys

# Be able to import ourselves.
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(here))


project = 'VEE'
copyright = '2015-{}, Mike Boers'.format(dt.datetime.utcnow().year)
version = '0.1'
release = '0.1'


master_doc = 'index'
# source_suffix = '.rst'
# templates_path = ['_templates']
# source_encoding = 'utf-8-sig'

exclude_patterns = ['_build']
# pygments_style = 'sphinx'
html_theme = 'nature'
html_static_path = ['_static']


extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
    'sphinx.ext.graphviz',
]

todo_include_todos = True

intersphinx_mapping = {'http://docs.python.org/': None}


def setup(app):
    app.add_stylesheet('custom.css')

