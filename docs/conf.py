# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import sys
from pathlib import Path

sys.path.append(str(Path().resolve()))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "py-build-cmake"
copyright = "2025, Pieter P"
author = "Pieter P"
release = "0.4.3"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx_design",
    # "_extension.gallery_directive",
    "myst_parser",
]

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_book_theme"
html_extra_path = ["_extra"]
html_static_path = ["_static"]
html_css_files = ["style.css"]
html_js_files = ["pypi-icon.js"]
html_title = "py-build-cmake"
html_logo = "images/py-build-cmake-logo.svg"
html_favicon = "images/py-build-cmake-logo.svg"
html_context = {
    "github_user": "tttapa",
    "github_repo": "py-build-cmake",
    "github_version": "0.4.3",
    "doc_path": "docs",
}
html_show_sourcelink = False
html_theme_options = {
    "use_edit_page_button": True,
    "logo": {
        "text": "py-build-cmake",
        # "link": "https://github.com/tttapa/py-build-cmake",
    },
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/tttapa/py-build-cmake",
            "icon": "fa-brands fa-github",
            "type": "fontawesome",
        },
        {
            "name": "PyPI",
            "url": "https://www.pypi.org/p/py-build-cmake",
            "icon": "fa-custom fa-pypi",
            "type": "fontawesome",
        },
    ],
    "pygments_light_style": "vs",
    "pygments_dark_style": "monokai",
    "show_toc_level": 3,
    "show_navbar_depth": 3,
}

# Options for extensions -----------------------------------------------------

myst_heading_anchors = 4
myst_enable_extensions = ["colon_fence"]
