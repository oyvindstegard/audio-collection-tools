# -*- coding: utf-8 -*-
#
# generate-playlists module
#
# Requires Python 3 and python-mutagen.
#
# Copyright (C) 2018, Øyvind Stegard <oyvind@stegard.net>

import os
import sys
import re
import mutagen
import fnmatch

# Extend this list to recognize more file types as audio files:
PLAYLIST_FILE_PATTERNS = ['*.mp3', '*.ogg', '*.flac', '*.m4a', '*.wav', '*.wma', '*.ape', '*.wv']

def write_pls(filename, audiofiles):
    if len(audiofiles) == 0:
        sys.stdout.write('Not writing {}: no files\n'.format(filename))
        return
        
    pltitle = os.path.splitext(os.path.basename(filename))[0]
    f = open(filename, 'w', encoding='utf8')
    sys.stdout.write('Writing PLS playlist: {} ({} audio files) ..\n'.format(filename, len(audiofiles)))
    f.write('[playlist]\n')
    for i, audiofile in enumerate(audiofiles, 1):
        filetitle = os.path.splitext(os.path.basename(audiofile))[0]
        f.write('Title{}={}\n'.format(i, filetitle))
        f.write('File{}={}\n'.format(i, audiofile))

    f.write('NumberOfEntries={}\n'.format(len(audiofiles)))
    f.write('X-Gnome-Title={}\n'.format(pltitle.capitalize()))
    f.write('Version=2\n')
    f.close()

def write_m3u(filename, audiofiles, utf8=True):
    if len(audiofiles) == 0:
        sys.stdout.write('Not writing {}: no files\n'.format(filename))
        return

    f = open(filename, 'w', encoding=('utf8' if utf8 else 'latin1'))
    sys.stdout.write('Writing M3U playlist \'{}\' ({} audio files) ..\n'.format(filename, len(audiofiles)))
    for path in audiofiles:
        f.write(path)
        f.write('\r\n')

    f.close()

def is_audio_file(filename):
    for p in PLAYLIST_FILE_PATTERNS:
        if fnmatch.fnmatch(os.path.basename(filename).lower(), p):
            return True

    return False

def relativize_audiofile_path(plfile, audiofile):
    return os.path.relpath(audiofile, os.path.dirname(plfile))
    
def list_audiofiles_recursively(dir='.'):
    audiofiles = []
    if os.path.isfile(dir):
        return [dir]
    
    for dir, subdirs, files in os.walk(dir):
        subdirs.sort()
        files.sort()
        audiofiles.extend([os.path.normpath(os.path.join(dir, f)) for f in filter(is_audio_file, files)])

    return audiofiles

def sort_mtime(files):
    files.sort(key=lambda f: os.path.getmtime(f), reverse=True)

def sort_date(audiofiles):
    def get_date(f):
        try:
            return Tags(f).get('date') or '_'
        except:
            return '_'

    audiofiles.sort(key=get_date, reverse=True)

def sort_genre(audiofiles):
    def get_genre(f):
        try:
            return Tags(f).get('genre') or '_'
        except:
            return '_'
        
    audiofiles.sort(key=get_genre)

def sort_track(audiofiles):
    def get_track(f):
        try:
            tn = Tags(f).get('tracknumber')
            if tn and '/' in tn:
                tn = tn.split('/')[0]

            return int(tn) if tn else 0
        except:
            return 0
        
    audiofiles.sort(key=get_track)

def sort_random(audiofiles):
    from random import shuffle
    shuffle(audiofiles)

def match_genre(compiled_regexp, audiofile):
    """Matches a genre regexp against genres stored in audio file tags.
    Returns boolean True or False.
    """
    try:
        genre = Tags(audiofile).get('genre')
        return bool(genre and compiled_regexp.search(genre))
    except:
        return False    

def generate_playlist(plspec):
    cwd = os.getcwd()
    os.chdir(os.path.dirname(plspec.plfile))
    audiofiles = []
    for d in plspec.dirs:
        audiofiles += list_audiofiles_recursively(d)

    if plspec.genrematch:
        audiofiles = [audiofile for audiofile in audiofiles
                      if match_genre(plspec.genrematch, audiofile) != plspec.genrematch_invert]

    if plspec.sortspec == 'mtime':
        sort_mtime(audiofiles)
    elif plspec.sortspec == 'genre':
        sort_genre(audiofiles)
    elif plspec.sortspec == 'date':
        sort_date(audiofiles)
    elif plspec.sortspec == 'track':
        sort_track(audiofiles)
    elif plspec.sortspec == 'random':
        sort_random(audiofiles)
    elif plspec.sortspec is not None:
        raise ValueError('Unknown sort criterium: {}'.format(plspec.sortspec))

    os.chdir(cwd)

    if plspec.plfile.endswith('m3u'):
        try:
            write_m3u(plspec.plfile, audiofiles, utf8=plspec.force_utf8)
        except UnicodeEncodeError:
            message = """Error: M3U playlist '{}' could not be written using latin-1
encoding, which is required by the spec. Consider using .m3u8 format
instead, or use --force-utf8 to write .m3u files with UTF-8 encoding.
This violates the spec, but may still work with many audio players.""".format(plspec.plfile)
            import textwrap
            from shutil import get_terminal_size as termsize
            sys.stderr.write(textwrap.fill(message, width=termsize().columns) + '\n')

    elif plspec.plfile.endswith('m3u8'):
        write_m3u(plspec.plfile, audiofiles, utf8=True)
    elif plspec.plfile.endswith('pls'):
        write_pls(plspec.plfile, audiofiles)
    else:
        raise ValueError('Unknown playlist format: {}'.format(plspec.plfile))

class Tags:
    """Simple wrapper around mutagen's "easy" tag reading API.

    Consolidates multiple tag values into single strings.
    """
    def __init__(self, filename):
        try:
            self.mutagen_file = mutagen.File(filename, easy=True)
        except Exception as e:
            sys.stderr.write("Could not read tags for file '{}': {}\n".format(filename, str(e)))
            self.mutagen_file = None

    def get(self, tagname):
        if not self.mutagen_file or not self.mutagen_file.tags:
            return None

        values = []
        if tagname.upper() in self.mutagen_file.tags:
            values = self.mutagen_file.tags.get(tagname.upper())
        elif tagname in self.mutagen_file.tags:
            values = self.mutagen_file.tags.get(tagname)
        
        if len(values) > 0:
            return ','.join(values)
        else:
            return None

    def tagnames(self):
        if not self.mutagen_file or not self.mutagen_file.tags:
            return []

class PlaylistSpec:
    def __init__(self, plfile, dirs,
                 force_utf8=False, sortspec=None, genrematch=None, genrematch_invert=False):
        self.plfile = plfile
        self.dirs = dirs
        self.force_utf8 = force_utf8
        self.sortspec = sortspec
        self.genrematch = genrematch
        self.genrematch_invert = genrematch_invert

    def __str__(self):
        gi = '!' if self.genrematch_invert else ''
        return 'PlaylistSpec{{{}, sortspec = {}, genrematch = {}{}, dirlist = {}}}'.format(
            self.plfile, self.sortspec, gi, self.genrematch, self.dirs)
