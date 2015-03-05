# -*- coding: utf-8 -*-

import sys
import os

here = os.path.dirname(os.path.abspath(__file__))

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'VEE'
copyright = u'2015, Mike Boers'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.

version = '0.1'
release = '0.1'


# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']


# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'


try:
    import sphinx_rtd_theme
except ImportError:
    print 'Could not import sphinx_rtd_theme'
    html_theme = 'default'
else:
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
    html_theme = "sphinx_rtd_theme"


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']


todo_include_todos = True


# Configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'http://docs.python.org/': None}
