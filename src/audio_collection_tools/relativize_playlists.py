# -*- coding: utf-8 -*-
#
# relativize-playlists
#
# Relativize paths in playlist files.
#
# Copyright 2018, Øyvind Stegard <oyvind@stegard.net>

import os
import sys
import re
from urllib.parse import unquote

class UnsupportedFormatError(Exception):
    pass

def relativize_m3u(basedir, infile, outfile):
    regexp = re.compile('^([^#].*)$')
    for line in infile:
        m = regexp.match(line)
        if m:
            audiofile = m.group(1)
            if audiofile.startswith('file://'):
                audiofile = unquote(audiofile[7:])

            line = os.path.relpath(os.path.realpath(audiofile), basedir) + '\n'

        outfile.write(line)

def relativize_pls(basedir, infile, outfile):
    regexp = re.compile('^(File[0-9]+)=(.*)$')

    for line in infile:
        m = regexp.match(line)
        if m:
            filenr = m.group(1)
            audiofile = m.group(2)
            if audiofile.startswith('file://'):
                audiofile = unquote(audiofile[7:])

            line = filenr + '=' + os.path.relpath(os.path.realpath(audiofile), basedir) + '\n'

        outfile.write(line)

def relativize(filename, force_utf8, keep_original):
    invokedir = os.getcwd()

    plfile = open(os.path.abspath(filename), 'r', encoding='utf8')
    if os.path.dirname(filename) == '':
        basedir = os.path.realpath(os.path.abspath('.'))
    else:
        basedir = os.path.realpath(os.path.abspath(os.path.dirname(filename)))

    try:
        os.chdir(basedir)
        name, suffix = os.path.splitext(os.path.basename(filename))
        tmpfilename = name + '.rel' + suffix
        tmpfile = open(os.path.join(basedir, tmpfilename), 'w', encoding='utf8')
        if filename.lower().endswith('.m3u'):
            if not force_utf8:
                plfile = open(plfile.name, 'r', encoding='latin1')
                tmpfile = open(tmpfile.name, 'w', encoding='latin1')

            relativize_m3u(basedir, plfile, tmpfile)
        elif filename.lower().endswith('.m3u8'):
            relativize_m3u(basedir, plfile, tmpfile)
        elif filename.lower().endswith('.pls'):
            relativize_pls(basedir, plfile, tmpfile)
        else:
            raise UnsupportedFormatError('Unsupported playlist type: {}'.format(filename))

        plfile.close()
        tmpfile.close()
        if keep_original:
            print('Wrote relativized playlist file: {}'.format(tmpfile.name))
        else:
            os.rename(os.path.basename(tmpfile.name), os.path.basename(plfile.name))
            print('Relativized playlist file: {}'.format(plfile.name))

    except UnicodeDecodeError as u:
        print('Character decoding error for playlist: {}, consider using option --force-utf8 if the file is .m3u'.format(filename))
        raise u
        
    finally:
        os.chdir(invokedir)
