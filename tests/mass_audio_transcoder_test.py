from audio_collection_tools import *
from audio_collection_tools.mass_audio_transcoder import *

from .fixtures import *

import os

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

# TODO:
# - test target path generation
# - test transcoding
