# Audio collection command line tools (Python)

This repository houses command line tools to manage audio collections
and playlists. The tools were written to perform batch tasks like
transferral of audio files and playlists to devices with limited
format support and automatically creating updated playlists.

The tools are written in Python and generally require Python 3. No
attempt at Python 2 compatibility is made by the author, even though
it may not require much work.

Only tested in unix-like environments, you mileage on the Windows
platform may vary. (Pull-reqs that fix compatibility issues are welcome
of course.)

## Requirements

- Python 3
- The Python mutagen library for reading audio file tags.
- ffmpeg command line tool, recentish version (mass-audio-transcoder
  only)

## Installation

    $ git clone https://github.com/oyvindstegard/audio-collection-tools.git
    $ python3 setup.py install

## The tools so far

### mass-audio-transcoder

This can be used to transcode an entire music collection to a certain
audio file format, using file names and directory structure based on
audio file tag metadata and naming templates. This tool requires the
`ffmpeg` command to be available.

It will accept any number of audio files and directories containing
audio files as input and process everything in parallel using ffmpeg.
By default, it uses all of the CPU cores available on the system to
make the process go as fast as possible, running multiple `ffmpeg`
processes.

It will also accept playlists as input and will transcode all files
referenced in the playlist to a target location. For playlists, the
default template will cause the files to be located under a single
directory named after the playlist file and use filenames which order
them like the order in the original playlist. This will make playlists
transferable to devices which don't really understand normal playlist
files.

See

    $ mass-audio-transcoder --help
    
for more details.


#### Usage example: creating an MP3 mirror of an existing audio collection

    $ mkdir /tmp/my-music-mp3
    $ mass-audio-transcoder -c mp3 /my-music-collection/ /tmp/my-music-mp3/

This requires that the source audio collection files have meta tags
attached to them, since the meta data determines the destination
directory structure based on a naming template.

#### TODO more examples


### generate-playlists

This tool can process directories containing audio files recursively
and create playlists, optionally filtering and sorting the playlists
on various criteria.

For instance, by filtering on a genre regexp, you can automatically
make genre-focused playlists from a larger collection.

See

    $ generate-playlists --help
    
for more details.


#### Usage example:

Create a playlist file `jazz.m3u` of all funk and jazz music with
randomized order:

    $ generate-playlists jazz.m3u:/path/to/my-audio-collection/,genre='jazz|funk',sort=random


### relativize-playlists

This tool can relativize the file paths in a playlist. This makes the
playlist more portable, e.g. when music collection is shared on a
network or moved to a different location.

See

    $ relativize-playlists --help
    
for more details.

#### Usage examples

TODO

## Development, issues and contributing

Bug reports and pull requests are welcome.

The tools have been developed in a Python 3 virtual environment, which
is recommended. To setup such an environment, execute the following in
the base directory of the project:

    $ pyvenv venv-dev
    $ source venv-dev/bin/activate
    $ python3 setup.py develop

### Running unit tests

    $ python3 setup.py test

### Project TODO

- Packaging: Use console_scripts entry point for command line scripts
  http://python-packaging.readthedocs.io/en/latest/command-line-scripts.html
- Refactor out common code from the tools into a common module.
- Add tests for `audio_collection_tools/mass_audio_transcoder.py`.
- Add option to `mass-audio-transcoder` which will structure
  destination files according to the structure of the sources
  (regardless of tag metadata).

## License

Distributed under the [GPL v3
license](https://opensource.org/licenses/GPL-3.0), this is free and
open source software.
