# -*- coding: utf-8 -*-
import setuptools
from src.audio_collection_tools import VERSION

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="audio-collection-tools",
    version=VERSION,
    author="Øyvind Stegard",
    author_email="oyvind@stegard.net",
    description="Misc tools for transcoding audio collections",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/oyvindstegard/audio-collection-tools/",
    packages=setuptools.find_packages('src'),
    package_dir={'':'src'},
    classifiers=[
        "Environment :: Console",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License (GPL)"
    ],
    scripts=[
        "src/mass-audio-transcoder",
        "src/generate-playlists",
        "src/relativize-playlists"
    ],
    setup_requires=[
        "setuptools_git",
        "pytest-runner",
    ],
    tests_require=[
        "pytest",
    ],
    install_requires=[
        "mutagen",
    ],
)
