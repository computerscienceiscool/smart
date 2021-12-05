# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))
#import stubs


# -- Project information -----------------------------------------------------

project = 'stubs'
copyright = '2021, Justin Laughlin'
author = 'Justin Laughlin'

# The full version, including alpha/beta/rc tags
release = '0.1.5'


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
        'sphinx.ext.autosummary',   # auto generates function/method/attribute summary lists
        'sphinx.ext.autodoc',       # auto generate documentation from docstrings
        'sphinx.ext.viewcode',
        'sphinx.ext.mathjax',       # tex math rendered with java
        'sphinx.ext.napoleon',      # numpy/google style docstrings
        'sphinx.ext.intersphinx',
]

##############################
# Napoleon Settings
##############################
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = True
napoleon_use_param = True
napoleon_use_rtype = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


autodoc_mock_imports = ["dolfin", "petsc4py", "mpi4py"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
#html_theme = 'alabaster'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
#html_static_path = ['_static']

##############################
# Autosummary Settings
##############################

autosummary_generate = True
# autodoc_default_flags = ['members', 'inherited-members']

##############################
# HTML Output Settings
##############################

# Try to load sphinx_rtd_theme otherwise fallback on default
try:
    import sphinx_rtd_theme
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]
    html_theme = 'sphinx_rtd_theme'
except ImportError:
    html_theme = 'default'

##############################
# Intersphinx Settings
##############################

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {'python': ('https://docs.python.org/3', None),
                       'numpy': ('https://numpy.org/doc/stable/', None)}
