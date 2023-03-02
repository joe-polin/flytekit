# -*- coding: utf-8 -*-
#
# Configuration file for the Sphinx documentation builder.
#
# This file does only contain a selection of the most common options. For a
# full list see the documentation:
# http://www.sphinx-doc.org/en/stable/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

flytekit_dir = os.path.abspath("../..")
flytekit_src_dir = os.path.abspath(os.path.join(flytekit_dir, "flytekit"))
plugins_dir = os.path.abspath(os.path.join(flytekit_dir, "plugins"))

for possible_plugin_dir in os.listdir(plugins_dir):
    dir_path = os.path.abspath((os.path.join(plugins_dir, possible_plugin_dir)))
    plugin_path = os.path.abspath(os.path.join(dir_path, "flytekitplugins"))
    if os.path.isdir(dir_path) and os.path.exists(plugin_path):
        sys.path.insert(0, dir_path)

sys.path.insert(0, flytekit_src_dir)
sys.path.insert(0, flytekit_dir)

# -- Project information -----------------------------------------------------

project = "Flytekit"
copyright = "2021, Flyte"
author = "Flyte"

# The full version, including alpha/beta/rc tags
release = "0.16.0b9"

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.todo",
    "sphinx.ext.viewcode",
    "sphinx.ext.doctest",
    "sphinx.ext.intersphinx",
    "sphinx.ext.coverage",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.graphviz",
    "sphinx-prompt",
    "sphinx_copybutton",
    "sphinx_panels",
    "sphinxcontrib.yt",
    "sphinx_tags",
    "sphinx_click",
]

# build the templated autosummary files
autosummary_generate = True

autodoc_typehints = "description"

suppress_warnings = ["autosectionlabel.*"]

# autosectionlabel throws warnings if section names are duplicated.
# The following tells autosectionlabel to not throw a warning for
# duplicated section names that are in different documents.
autosectionlabel_prefix_document = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# The suffix(es) of source filenames.
# You can specify multiple suffix as a list of string:
#
# source_suffix = ['.rst', '.md']
source_suffix = ".rst"

# The master toctree document.
master_doc = "index"

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = None

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path .
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"
html_title = "Flyte"

html_theme_options = {
    "light_css_variables": {
        "color-brand-primary": "#4300c9",
        "color-brand-content": "#4300c9",
    },
    "dark_css_variables": {
        "color-brand-primary": "#9D68E4",
        "color-brand-content": "#9D68E4",
    },
    # custom flyteorg furo theme options
    "github_repo": "flytekit",
    "github_username": "flyteorg",
    "github_commit": "master",
    "docs_path": "docs/source",  # path to documentation source
}

templates_path = ["_templates"]

# The default sidebars (for documents that don't match any pattern) are
# defined by theme itself.  Builtin themes are using these templates by
# default: ``['localtoc.html', 'relations.html', 'sourcelink.html',
# 'searchbox.html']``.
# html_sidebars = {"**": ["logo-text.html", "globaltoc.html", "localtoc.html", "searchbox.html"]}


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = []

# Custom sidebar templates, must be a dictionary that maps document names
# to template names.
#
html_logo = "flyte_circle_gradient_1_4x4.png"
html_favicon = "flyte_circle_gradient_1_4x4.png"

pygments_style = "tango"
pygments_dark_style = "native"

html_context = {
    "home_page": "https://docs.flyte.org",
}

# -- Options for HTMLHelp output ---------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = "flytekitdoc"

# -- Options for LaTeX output ------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #
    # 'papersize': 'letterpaper',
    # The font size ('10pt', '11pt' or '12pt').
    #
    # 'pointsize': '10pt',
    # Additional stuff for the LaTeX preamble.
    #
    # 'preamble': '',
    # Latex figure (float) alignment
    #
    # 'figure_align': 'htbp',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (master_doc, "flytekit.tex", "Flytekit Documentation", "Flyte", "manual"),
]

# -- Options for manual page output ------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [(master_doc, "flytekit", "Flytekit Documentation", [author], 1)]

# -- Options for Texinfo output ----------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    (
        master_doc,
        "flytekit",
        "Flytekit Documentation",
        author,
        "flytekit",
        "Python SDK for Flyte (https://flyte.org).",
        "Miscellaneous",
    ),
]

# -- Extension configuration -------------------------------------------------
# intersphinx configuration
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "flytectl": ("https://flytectl.readthedocs.io/en/latest/", None),
    "idl": ("https://flyteidl.readthedocs.io/en/latest/", None),
    # "flytectl": ("/Users/yourusername/go/src/github.com/flyteorg/flytectl/docs/build/html", None),
    "cookbook": ("https://flytecookbook.readthedocs.io/en/latest/", None),
    "flyte": ("https://flyte.readthedocs.io/en/latest/", None),
}

inheritance_graph_attrs = {
    "resolution": 300.0,
}

inheritance_node_attrs = {
    "bgcolor": "aliceblue",
}

inheritance_edge_attrs = {
    "color": "darkgray",
}

autoclass_content = "both"

# Tags config
tags_create_tags = True
tags_page_title = "Tag"
tags_overview_title = "All Tags"
