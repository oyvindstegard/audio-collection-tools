# -*- coding: utf-8 -*-
#
# mass-audio-transcoder module
#
# Mass parallel Audio Transcoder ffmpeg frontend.
# Requires: Python 3, python-mutagen and a recent-ish (2017/18) ffmpeg command
# in PATH.
#
# Copyright 2018-2020, Øyvind Stegard <oyvind@stegard.net>

import sys
import os, shutil, subprocess
import re
from urllib.parse import unquote
import fnmatch
from collections import OrderedDict
import mutagen

import logging
import logging.handlers
import multiprocessing

# ffmpeg option templates for various transcoding targets
# for AAC targets, disable album art copying, since it's unreliable with ffmpeg
FFMPEG_EXECUTABLE = 'ffmpeg'
FFMPEG_CODEC_OPTS = {'mp3':      ['-codec:a libmp3lame',
                                  '<-qscale:a +transcode_quality+> <-b:a +transcode_bitrate+k>',
                                  '-id3v2_version 3'],
                     'aac':      ['-codec:v copy -codec:a aac',
                                  '<-vbr +transcode_quality+> <-b:a +transcode_bitrate+k>'],
                     'fdkaac':   ['-codec:v copy -codec:a libfdk_aac',
                                  '<-vbr +transcode_quality+> <-b:a +transcode_bitrate+k>'],
                     'vorbis':   ['-codec:a libvorbis',
                                  '<-qscale:a +transcode_quality+> <-b:a +transcode_bitrate+k>'],
                     'copy':     []
                     }

# Ogg audio files have metadata attached to audio stream instead of
# container, which makes a difference for ffmpeg.
FFMPEG_INPUT_FILE_OPTS = {'ogg': ['-map_metadata 0:s:0']}

FFMPEG_CODEC_EXT  = {'vorbis': 'ogg', 'mp3':'mp3', 'aac':'m4a', 'fdkaac':'m4a', 'copy':'*'}
FFMPEG_DEFAULT_CODEC = 'mp3'

# Basic list of supported input formats. Other formats will work as long as both
# mutagen and ffmpeg understands how to decode them.
INPUT_AUDIOFILE_PATTERNS = ['*.mp3', '*.ogg', '*.flac', '*.m4a', '*.mpc', '*.wav']

# Default templates for naming of transcoded files:
DEFAULT_TEMPLATE = '<albumartist_or_artist>< - +album+>< disc +discnumber+>/<track+. ><title>'
DEFAULT_TEMPLATE_PLAYLIST = '<playlist_name>/<playlist_filenumber>. <title> - <artist>'

# Wrap logger with simple inter-process mutex-locking to avoid output
# mess when multiple subprocesses are logging. This becomes
# inefficient with large amounts logging output, but should not matter
# much for this tool.
class SynchronizedLog:
    def __init__(self, log, lock):
        self.log = log
        self.lock = lock
        self.warn_enabled = True
    def info(self, msg, *args, **kwargs):
        with self.lock:
            self.log.info(msg, *args, **kwargs)
    def debug(self, msg, *args, **kwargs):
        with self.lock:
            self.log.debug(msg, *args, **kwargs)
    def warn(self, msg, *args, **kwargs):
        if not self.warn_enabled: return
        with self.lock:
            self.log.warning(msg, *args, **kwargs)
    def error(self, msg, *args, **kwargs):
        with self.lock:
            self.log.error(msg, *args, **kwargs)
    def setLevel(self, level):
        with self.lock:
            self.log.setLevel(level)
    def disableWarn(self):
        self.warn_enabled = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(processName)s] %(levelname)-8s %(message)s')
LOG_LOCK = multiprocessing.Lock()
LOG = SynchronizedLog(logging.getLogger('mpat'), LOG_LOCK)

class ApplicationError(Exception):
    pass

class UnsupportedFileError(ApplicationError):
    def __init__(self, message, filetype):
        super().__init__(message)
        self.filetype = filetype

class CommandError(ApplicationError):
    pass

class TemplateError(ApplicationError):
    pass

class Tags:
    """Thin wrapper around mutagen's "easy" tag reading API.

    If a tag has multiple values, they are joined before returned.
    """
    def __init__(self, filename):
        try:
            self.mutagen_file = mutagen.File(filename, easy=True)
        except Exception as e:
            LOG.warn('Could not read tags for file: {}, {}\n'.format(filename, str(e)))
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

            
def ffmpeg_check_version():
    """Checks version of ffmpeg in path. Returns version as a string on success."""
    ffmpeg_path = shutil.which(FFMPEG_EXECUTABLE)
    if not ffmpeg_path:
        raise CommandError("Missing '{}' command in system PATH".format(FFMPEG_EXECUTABLE))

    output = subprocess.check_output([ffmpeg_path, '-nostdin', '-version'])
    vmatch = re.search(r'^ffmpeg version ([^\s]+)', output.decode())
    if vmatch:
        return vmatch.group(1)
    else:
        raise CommandError("Unable to determine ffmpeg version for executable '{}'".format(ffmpeg_path))

def ffmpeg_build_args(inputfile, outputfile, codec, transcode_quality=None, transcode_bitrate=None):
    args = ['-nostdin', '-i', inputfile, '-y', '-map_chapters', '-1']
    var_resolver = {'transcode_quality':transcode_quality, 'transcode_bitrate':transcode_bitrate}

    inputfiletype = get_normalized_extension(inputfile)
    if inputfiletype and inputfiletype in FFMPEG_INPUT_FILE_OPTS:
        for argpart in FFMPEG_INPUT_FILE_OPTS[inputfiletype]:
            args += expand_template(argpart, var_resolver).split()
        
    for argpart in FFMPEG_CODEC_OPTS[codec]:
        args += expand_template(argpart, var_resolver).split()

    args.append(outputfile)
    
    return args

def get_normalized_extension(filename):
    return os.path.splitext(filename)[1].lower()[1:]

def is_audio_file(filename):
    for p in INPUT_AUDIOFILE_PATTERNS:
        if fnmatch.fnmatch(os.path.basename(filename).lower(), p):
            return True

    return False

def is_pls_playlist(filename):
    return fnmatch.fnmatch(os.path.basename(filename).lower(), '*.pls')

def is_m3u_playlist(filename):
    for pattern in ['*.m3u','*.m3u8']:
        if fnmatch.fnmatch(os.path.basename(filename).lower(), '*.m3u'):
            return True

    return False

def is_playlist(filename):
    return is_pls_playlist(filename) or is_m3u_playlist(filename)

def get_playlist_name(filename):
    return os.path.splitext(os.path.basename(filename))[0]

def extract_pls_paths(plfile):
    """Extract audio file paths from PLS playlist. Argument must be open file handle."""
    paths = []
    regexp = re.compile('^(File[0-9]+)=(.*)$')
    for line in plfile:
        m = regexp.match(line)
        if m and len(m.group(2).strip()) > 0:
            audiofile = m.group(2)
            if audiofile.startswith('file://'):
                audiofile = unquote(audiofile[7:])
            
            if is_audio_file(audiofile):
                paths.append(audiofile)

    return paths

def extract_m3u_paths(plfile):
    """Extract audio file paths from M3U playlist. Argument must be open file handle."""
    paths = []
    regexp = re.compile('^([^#].*)$')
    for line in plfile:
        m = regexp.match(line)
        if m and len(m.group(1).strip()) > 0:
            audiofile = m.group(1)
            if audiofile.startswith('file://'):
                audiofile = unquote(audiofile[7:])

            if is_audio_file(audiofile):
                paths.append(audiofile)

    return paths

def get_audiofile_paths_from_playlist(filename):
    """Process playlist, return list of absolute paths to all audio files.."""

    invokedir = os.getcwd()
    pldir = os.path.dirname(filename)
    if pldir == '':
        pldir = '.'

    try:
        plfile = open(filename, 'r', encoding='utf8')
        if is_pls_playlist(filename):
            paths = extract_pls_paths(plfile)
        elif is_m3u_playlist(filename):
            paths = extract_m3u_paths(plfile)
        else:
            raise UnsupportedFileError('Unknown playlist type: {}'.format(filename),
                                       os.path.splitext(filename)[1])

        os.chdir(pldir)
        return [os.path.abspath(p) for p in paths]
        
    finally:
        os.chdir(invokedir)
        plfile.close()
        

def get_audiofile_paths(directory):
    """Process directory and return list of audio files.

    If directory is actually a file, only that file is returned as a
    single element list, if it is an audio file.
    
    Always returns absolute paths.
    """

    if os.path.isfile(directory):
        if is_audio_file(directory):
            return [os.path.abspath(directory)]
        else:
            LOG.warn('Not a known audio file type: {}'.format(directory))
            return []
    
    paths = []
    for dir, subdirs, files in os.walk(directory):
        subdirs.sort()
        files.sort()
        paths.extend([os.path.normpath(os.path.join(dir, f)) for f in filter(is_audio_file, files)])

    return [os.path.abspath(p) for p in paths]

PATH_CLEANING_PATTERNS = [(re.compile(p), r) for p, r in
                          [(r'[?*:;<>|\\]', ''),
                           (r'["`˝]', '\''),
                           (r'^[. ]+', ''),
                           (r'[. ]+$', ''),
                           (r'[.]+/', '/'),
                           (r'/[.]+', '/'),
                           (r'\s{2,}', ' '),
                           (r'\s*/\s*', '/'),
                           (r'/{2,}', '/'),
                           (r'([^/]{200,})', lambda m: m.group(1)[:200])]]
def clean_path(path):
    """Remove file system unsafe characters from file path, ensure path components stay within typical file system limits."""
    for pattern, replacement in PATH_CLEANING_PATTERNS:
        path = re.sub(pattern, replacement, path)

    return path

def expand_template(template, variable_resolver, allow_slash_in_var_values=True):
    """Expands a template with <var> placeholders.

    Syntax:
    'Some template with <thisvar>, <thatvar+suffix> and <prefix+othervar+suffix>'

    When plus chars (+) are used, it denotes a literal suffix/prefix that
    should only be included if the value exists. (Some audio files may
    lack tags, etc.)

    Literal angle brackets cannot be used at all in templates, and
    plus chars cannot be used in suffix or prefix inside a variable
    expression.

    The variable resolver should be a function which accepts a single
    argument, namely a variable name. It should return None for
    variables which cannot be resolved.

    """

    def resolver(v):
        if isinstance(variable_resolver, dict):
            return variable_resolver.get(v)
        else:
            return variable_resolver(v)
        
    def replacer(m):
        if not m.group(1):
            return ''

        parts = m.group(1).split('+', 2)
        cond_prefix = ''
        cond_suffix = ''
        if len(parts) == 1:
            var = parts[0]
        elif len(parts) == 2:
            var = parts[0]
            cond_suffix = parts[1]
        elif len(parts) == 3:
            cond_prefix = parts[0]
            var = parts[1]
            cond_suffix = parts[2]
        else:
            raise TemplateError('Illegal number of elements in expression "<{}>"'.format(m.group(1)))
            
        value = resolver(var)
        if value and not allow_slash_in_var_values:
            value = value.replace('/', '-')

        return '' if value is None else '{}{}{}'.format(cond_prefix, value, cond_suffix)
        
    return re.sub(r'<([^<>]+)?>', replacer, template)

def zeropad(n, length):
    """Zeropad a positive number to given length."""
    return str(n).zfill(length)

def tag_variable_resolver(source):
    """Returns a function which can be used as template variable resolver
    for a particular audio file source based on file tag values.

    """
    tags = Tags(source.filepath)

    def resolver(var):
        var = var.lower()
        if var in ['a', 'artist']:
            return tags.get('artist')
        elif var in ['b', 'album']:
            return tags.get('album')
        elif var in ['t', 'title']:
            return tags.get('title')
        elif var in ['aa', 'albumartist']:
            return tags.get('albumartist')
        elif var in ['aaa', 'albumartist_or_artist']:
            val = tags.get('albumartist')
            if not val:
                val = tags.get('artist')

            return val
        elif var in ['tn', 'track', 'tracknumber']:
            val = tags.get('tracknumber')
            if val and '/' in val:
                val = val.split('/')[0]

            try:
                return zeropad(int(val), 2) if val else None
            except:
                return None
        elif var in ['tt', 'tracktotal']:
            val = tags.get('tracktotal')
            if not val:
                val = tags.get('tracknumber')
                if not '/' in val:
                    return None
                else:
                    val = val.split('/')[1]

            try:
                return zeropad(int(val), 2) if val else None
            except:
                return None
        elif var in ['dn', 'discnumber']:
            val = tags.get('discnumber')
            try:
                return zeropad(val, 2) if val else None
            except:
                return None
        elif var == 'filename':
            return source.basename(True)
        elif var == 'filename_noext':
            return source.basename(False)
        elif var == 'parentdir_basename':
            return source.parentdir_basename()
        elif var == 'ext':
            return source.filetype()
        elif var == 'filenumber':
            return zeropad(source.filenumber, len(str(source.totalfiles)))
        elif var == 'totalfiles':
            return str(source.totalfiles)
        elif var == 'playlist_name':
            return get_playlist_name(source.playlist_file) if source.playlist_file else None
        elif var == 'playlist_filenumber':
            if source.playlist_filenumber and source.playlist_totalfiles:
                return zeropad(source.playlist_filenumber, len(str(source.playlist_totalfiles)))
            else:
                return None
        elif var == 'playlist_totalfiles':
            if source.playlist_totalfiles:
                return str(source.playlist_totalfiles)
            else:
                return None

        else:
            # Try rest of tags as fallback
            return tags.get(var)

    return resolver

from enum import Enum
class Status(Enum):
    """Processing status"""
    INIT = 0
    READY = 1
    SKIPPED_NAME_COLLISION = 2
    SKIPPED_TARGETPATH_EXISTS = 3
    SKIPPED_TARGETPATH_NEWER = 4
    SKIPPED_TARGETPATH_EQ_SOURCEPATH = 5
    SKIPPED_GENERATE_TARGETPATH = 6
    FAILED_ABORTED = 7
    FAILED_FFMPEG = 8
    FAILED_IO = 9
    COMPLETED = 10

    def is_failed(self):
        return self.name.startswith('FAILED')

    def is_skipped(self):
        return self.name.startswith('SKIPPED')

    def is_completed(self):
        return self is Status.COMPLETED

class OverwriteMode(Enum):
    """Overwrite modes"""
    NO_OVERWRITE = 0
    OVERWRITE = 1
    OVERWRITE_IF_OLDER = 2
    
class TranscodeSpec:
    """Transcoding options"""
    def __init__(self, codec, force_transcode, quality=None, bitrate=None):
        self.codec = codec
        self.force_transcode = bool(force_transcode)
        self.quality = quality
        self.bitrate = bitrate

class Source:
    """Represents an audio file source (unit of transcoding work). Also
    holds some contextual info about playlist, if file is part of a
    playlist.

    """
    def __init__(self, filepath, transcode_spec,
                 playlist_file=None, playlist_filenumber=None, playlist_totalfiles=None):
        self.filepath = filepath
        self.transcode_spec = transcode_spec

        self.filenumber = -1
        self.totalfiles = -1

        self.playlist_file = playlist_file
        self.playlist_filenumber = playlist_filenumber
        self.playlist_totalfiles = playlist_totalfiles

    def basename(self, include_ext=True):
        """Return basename of audio file, optionally without the extension."""
        bn = os.path.basename(self.filepath)
        return bn if include_ext else os.path.splitext(bn)[0]

    def filetype(self):
        """Return lower case normalized audio file type (extension).

        Returns None if unable to determine.
        """

        ext = get_normalized_extension(self.filepath)
        return ext if len(ext) > 0 else None

    def parentdir_basename(self):
        """Return basename of parent directory."""
        return os.path.basename(os.path.dirname(self.filepath))

    def __str__(self):
        template = 'Source{{{}, filenumber={}, totalfiles={}'
        if self.playlist_file:
            template += ', playlist_file={}, playlist_filenumber={}, playlist_totalfiles={}'
        template += '}}'

        return template.format(self.filepath, self.filenumber, self.totalfiles,
                               self.playlist_file, self.playlist_filenumber, self.playlist_totalfiles)

class WorkUnit:
    """Unit of work, a source, a target file and processing status."""
    def __init__(self, source, status=Status.INIT, targetpath=None):
        self.source = source
        self.status = Status
        self.targetpath = targetpath

    def __str__(self):
        return "WorkUnit{{{}, status: {}, targetpath: {}}}".format(
            str(self.source), str(self.status), str(self.targetpath))

def generate_target_path(source, template, destdir):
    """Creates target path up to and including the final directory.

    If the template and cleanups result in an empty string, a fallback
    is used where the original filename and parent directory are used
    under destdir.
    """
    
    var_resolver = tag_variable_resolver(source)
    result = expand_template(template, var_resolver, False)
    result = clean_path(result).strip()

    if len(result) == 0 or result.endswith('/') or os.path.isabs(result):
        result = clean_path(os.path.join(source.parentdir_basename(), source.basename(False)))
        LOG.warn("Template expansion resulted in bad file path for source file '{}', using fallback naming: '{}'".format(source.filepath, result))

    if source.transcode_spec.codec != 'copy':
        ext = FFMPEG_CODEC_EXT[source.transcode_spec.codec]
    else:
        ext = source.filetype()
        
    if not result.endswith('.' + ext):
        result += '.' + ext

    abspath = os.path.join(destdir, result)

    return abspath

def prepare_work_units(sources, destdir, naming_template, playlist_naming_template, overwritemode):
    """Returns a list of WorkUnit instances.

    Checks input material for naming collisions and other problems.

    Work units which cannot be executed, for various reasons, are
    given an appropriate status and logged.

    """

    targetpaths = {}
    work_units = []
    for source in sources:
        work_unit = WorkUnit(source)
        work_units.append(work_unit)

        template = naming_template if not source.playlist_file else playlist_naming_template
        targetpath = generate_target_path(source, template, destdir)
        if not targetpath:
            work_unit.status = Status.SKIPPED_GENERATE_TARGETPATH
            continue
        
        work_unit.targetpath = targetpath

        if source.filepath == targetpath:
            work_unit.status = Status.SKIPPED_TARGETPATH_EQ_SOURCEPATH
            LOG.warn("Source file '{}' has itself as target, skipping.".format(source.filepath))
            continue

        if targetpath in targetpaths:
            work_unit.status = Status.SKIPPED_NAME_COLLISION
            colliding_source = targetpaths[targetpath]
            source_desc = '{}#{}:{}'.format(source.playlist_file, source.playlist_filenumber, source.filepath) if source.playlist_file else source.filepath
            colliding_source_desc = '{}#{}:{}'.format(colliding_source.playlist_file, colliding_source.playlist_filenumber, colliding_source.filepath) if colliding_source.playlist_file else colliding_source.filepath
            
            LOG.warn("Naming collision between source '{}' and '{}' for target path '{}', using first source".format(colliding_source_desc, source_desc, targetpath))
            continue
        else:
            targetpaths[targetpath] = source

        if os.path.exists(targetpath):
            if overwritemode is OverwriteMode.NO_OVERWRITE:
                work_unit.status = Status.SKIPPED_TARGETPATH_EXISTS
                LOG.warn("Source file '{}' has target path '{}' which already exists and overwrite is off, skipping".format(source.filepath, targetpath))
                continue
            elif overwritemode is OverwriteMode.OVERWRITE_IF_OLDER and os.path.getmtime(targetpath) >= os.path.getmtime(source.filepath):
                work_unit.status = Status.SKIPPED_TARGETPATH_NEWER
                LOG.warn("Source file '{}' has target path '{}' which already exists and is newer, skipping".format(source.filepath, targetpath))
                continue

        
        work_unit.status = Status.READY

    return work_units
