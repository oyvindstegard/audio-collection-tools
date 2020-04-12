from audio_collection_tools import *
from audio_collection_tools.mass_audio_transcoder import *

from .fixtures import *

import os
import shutil

# Eval main executable script for testing parts of it
with open('src/mass-audio-transcoder') as scriptfile:
    code = compile(scriptfile.read(), 'mass-audio-transcoder', 'exec')
    exec(code)

# Input scanning
def test_scan_inputs_directory(audio_tmpdir):
    sources = scan_inputs([audio_tmpdir], TranscodeSpec('mp3', False))
    sources.sort(key=lambda s: s.filepath)

    assert len(sources) == 10

    assert sources[0].filepath.endswith('audio/audio.m4a')
    assert sources[1].filepath.endswith('audio/audio.mp3')
    assert sources[2].filepath.endswith('audio/audio.ogg')
    assert sources[3].filepath.endswith('audio/subdir/audio.flac')
    assert sources[4].filepath.endswith('audio/subdir/audio.wav')
    assert sources[5].filepath.endswith('audio/tracks/01.ogg')
    assert sources[6].filepath.endswith('audio/tracks/02.ogg')
    assert sources[7].filepath.endswith('audio/tracks/03.ogg')
    assert sources[8].filepath.endswith('audio/tracks/04.ogg')
    assert sources[9].filepath.endswith('audio/tracks/05.ogg')

def test_scan_inputs_files(audio_tmpdir):
    inputs = [os.path.join(audio_tmpdir, filepath) for filepath in ['audio.ogg', 'tracks/01.ogg']]
    sources = scan_inputs(inputs, TranscodeSpec('mp3', False))
    sources.sort(key=lambda s: s.filepath)

    assert len(sources) == 2
    
    assert sources[0].filepath.endswith('audio/audio.ogg')
    assert sources[1].filepath.endswith('audio/tracks/01.ogg')

def test_scan_inputs_m3u_playlist(audio_tmpdir):
    sources = scan_inputs([os.path.join(audio_tmpdir, 'pl/pl.m3u')], TranscodeSpec('mp3', False))

    assert len(sources) == 3

    assert sources[0].filepath.endswith('tracks/01.ogg')
    assert sources[1].filepath.endswith('tracks/03.ogg')
    assert sources[2].filepath.endswith('tracks/05.ogg')

    for fn, source in enumerate(sources, 1):
        assert source.playlist_filenumber == fn
        assert source.playlist_totalfiles == 3
        assert source.playlist_file.endswith('pl/pl.m3u')

def test_scan_inputs_pls_playlist(audio_tmpdir):
    sources = scan_inputs([os.path.join(audio_tmpdir, 'pl/pl.pls')], TranscodeSpec('mp3', False))

    assert len(sources) == 2
    
    assert sources[0].filepath.endswith('tracks/02.ogg')
    assert sources[1].filepath.endswith('tracks/04.ogg')

    for fn, source in enumerate(sources, 1):
        assert source.playlist_filenumber == fn
        assert source.playlist_totalfiles == 2
        assert source.playlist_file.endswith('pl/pl.pls')

def test_scan_inputs_no_transcode_for(audio_tmpdir):
    sources = scan_inputs([audio_tmpdir], TranscodeSpec('mp3', False), ['ogg'])

    assert len(sources) == 10

    for source in sources:
        if source.filetype() == 'ogg':
            assert source.transcode_spec.codec == 'copy' and source.transcode_spec.force_transcode == False
        else:
            assert source.transcode_spec.codec == 'mp3'

# Testing overwrite modes
def test_prepare_workunits_no_overwrite(audio_tmpdir, empty_tmpdir):
    sources = scan_inputs([os.path.join(audio_tmpdir, 'audio.mp3')], TranscodeSpec('copy', False))
    assert len(sources) == 1
    
    shutil.copyfile(sources[0].filepath, os.path.join(empty_tmpdir, 'B - B title.mp3'))

    work_units = prepare_work_units(sources, empty_tmpdir, '<artist> - <title>', '<artist> - <title>', OverwriteMode.NO_OVERWRITE)

    assert len(work_units) == 1
    assert work_units[0].status == Status.SKIPPED_TARGETPATH_EXISTS

def test_prepare_workunits_overwrite(audio_tmpdir, empty_tmpdir):
    sources = scan_inputs([os.path.join(audio_tmpdir, 'audio.mp3')], TranscodeSpec('copy', False))
    assert len(sources) == 1
    
    shutil.copyfile(sources[0].filepath, os.path.join(empty_tmpdir, 'B - B title.mp3'))

    work_units = prepare_work_units(sources, empty_tmpdir, '<artist> - <title>', '<artist> - <title>', OverwriteMode.OVERWRITE)

    assert len(work_units) == 1
    assert work_units[0].status == Status.READY
    

def test_prepare_workunits_overwrite_if_older(audio_tmpdir, empty_tmpdir):
    sources = scan_inputs([os.path.join(audio_tmpdir, 'audio.mp3')], TranscodeSpec('copy', False))
    assert len(sources) == 1
    
    shutil.copyfile(sources[0].filepath, os.path.join(empty_tmpdir, 'B - B title.mp3'))

    work_units = prepare_work_units(sources, empty_tmpdir, '<artist> - <title>', '<artist> - <title>', OverwriteMode.OVERWRITE_IF_OLDER)

    assert len(work_units) == 1
    assert work_units[0].status == Status.SKIPPED_TARGETPATH_NEWER

    # Make source newer than target, which should allow overwrite
    import time
    now = time.time()
    os.utime(sources[0].filepath, (now, now))
    os.utime(os.path.join(empty_tmpdir, 'B - B title.mp3'), (now-3600,now-3600))
    work_units = prepare_work_units(sources, empty_tmpdir, '<artist> - <title>', '<artist> - <title>', OverwriteMode.OVERWRITE_IF_OLDER)

    assert len(work_units) == 1
    assert work_units[0].status == Status.READY


# TODO:
# - test actual transcoding
