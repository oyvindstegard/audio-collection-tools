# Audio collection command line tools (Python)

This repository houses command line tools to manage audio collections
and playlists. The tools were written to perform batch tasks like
transferral of audio files and playlists to devices with limited
format support and automatically creating updated playlists.

The tools are written in Python and generally require Python 3. No
attempt at Python 2 compatibility is made by the author, even though
it may not require much work.

Only tested in unix-like environments, you mileage on the Windows
platform may vary. However, the code is free of shell interpreted
command execution and platform specifics in that regard. (Pull-reqs
that fix compatibility issues are welcome.)

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
default template will cause the files to be located under a directory
named after the playlist file and use filenames which order them like
the order in the original playlist. This will make playlists
compatible with devices and players that do not really understand
normal playlist files. To use playlists just as sources for audio
files, change the template to be the same as for regular inputs, see
options `--playlist-template` and `--template`. All playlists provided
as input arguments are also written to the target root directory, with
contents updated to reflect the paths of the transcoded files instead
of the originals.

See:

    $ mass-audio-transcoder --help
    
and examples below for more details.

#### Naming templates

Target file paths are named according to templates. The templates may
introduce structure in the form of sub directories by including
slashes (directory separators).

The default naming templates for audio files that are not sourced from
a playlist are:

    <albumartist_or_artist>< - +album+>/<track+. ><title>
    
Template variables are enclosed in "<..>" and will typically be
metadata from audio file tags, such as in the default template shown
above. For details about this syntax and the available variables, see
`mass-audio-transcoder --help-templates`.

The default naming template for audio files that are sourced from
playlists is:

    <playlist_name>/<playlist_filenumber>. <title> - <artist>
    
This causes a top level directory named after the playlist file to be
created, and all audio files referenced in the playlist will have
their transcoded target files placed under that directory. They will
be numbered according to their number in the source playlist.

#### Example 1: creating an MP3 mirror of an existing audio collection

    $ mkdir /tmp/my-music-mp3
    $ mass-audio-transcoder /my-music-collection/ /tmp/my-music-mp3/

This requires that the source audio collection files have meta tags
attached to them, since the meta data determines the destination
directory structure based on a naming template.

The default codec is MP3. Other available codecs are AAC, Vorbis and a
special codec 'copy' which does no transcoding at all.

#### Example 2: copy all audio files referenced in multiple playlists

    $ mkdir /tmp/playlists-and-files
    $ mass-audio-transcoder -c copy ~/Music/list1.pls ~/Music/list2.m3u ~/Music/favorites.m3u \
      /tmp/playlists-and-files/

This will copy all audio files referenced in the provided playlists to
a new structure under the target location. Since we're using `-c
copy`, no transcoding will occur. Each playlist will get its own top
level directory, and the playlist files will be copied into these
directories (default playlist naming template). Finally, the playlist
files themselves will be generated in the target directory.

If two or more lists reference some of the same files, this will cause
the audio files to be duplicated into the different playlist folders,
since the default play. See example 3 to avoid this.

#### Example 3: copy audio files in playlists, but use standard file structure

    $ mkdir /tmp/playlists-and-files
    $ mass-audio-transcoder -c copy --playlist-template '<albumartist_or_artist>< - +album+>/<track+. ><title>' \
                            ~/Music/list1.pls ~/Music/list2.m3u ~/Music/favorites.m3u \
                            /tmp/playlists-and-files/
                            
This will copy all audio files referenced in the playlists to the
target location using a naming template which structures the audio
files in artist-album-folders at the top level (the default template
for audio files and directory sources). In this case, if the same
audio file is referenced by multiple playlists, it will cause a naming
collision warning, and the file will only be transcoded once, which is
typically desirable. The playlists generated in the target directory
will still reference all the files properly.


### generate-playlists

This tool can process directories containing audio files recursively
and create playlists, optionally filtering and sorting the playlists
on various criteria.

For instance, by filtering on a genre regexp, you can automatically
make genre-focused playlists from a larger collection.

See:

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

See:

    $ relativize-playlists --help
    
for more details.

## Development, issues and contributing

Bug reports and pull requests are welcome.

The tools have been developed in a Python 3 virtual environment, which
is recommended. To setup such an environment, execute the following in
the base directory of the project:

    $ python3 -m venv venv-dev
    $ source venv-dev/bin/activate
    $ python3 setup.py develop

### Running unit tests

    $ python3 setup.py test

### Project TODO

- Packaging: Use console_scripts entry point for command line scripts
  http://python-packaging.readthedocs.io/en/latest/command-line-scripts.html
- Refactor out common code from the tools into a common module.
- Add tests for `audio_collection_tools/mass_audio_transcoder.py`.
- Add option to `mass-audio-transcoder` which will structure target
  files according to the structure of the sources (regardless of tag
  metadata).

## License

Distributed under the [GPL v3
license](https://opensource.org/licenses/GPL-3.0), this is free and
open source software.
