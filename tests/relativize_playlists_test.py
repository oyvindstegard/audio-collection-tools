from audio_collection_tools import *
from audio_collection_tools.generate_playlists import generate_playlist, PlaylistSpec
from audio_collection_tools.relativize_playlists import *

from .fixtures import *

import os
import re

# Tests

def test_relativize_pls_playlist(pls_tmpfile, audio_tmpdir):
    generate_playlist(PlaylistSpec(pls_tmpfile, [audio_tmpdir]))

    basedir = os.path.commonpath([os.path.dirname(pls_tmpfile), audio_tmpdir])
    pls_relativized = pls_tmpfile + '.rel'

    in_fh = open(pls_tmpfile, 'r')
    out_fh = open(pls_relativized, 'w')

    relativize_pls(basedir, in_fh, out_fh)

    in_fh.close()
    out_fh.close()

    with open(pls_relativized, "r") as fh:
        for line in fh:
            m = re.match('^File[0-9]+=(.*)$', line)
            if m:
                path = m.group(1)
                assert not os.path.isabs(path)
                assert os.path.isfile(os.path.join(basedir, path))

    os.remove(pls_relativized)

def test_relativize_m3u_playlist(m3u_tmpfile, audio_tmpdir):
    generate_playlist(PlaylistSpec(m3u_tmpfile, [audio_tmpdir]))

    basedir = os.path.commonpath([os.path.dirname(m3u_tmpfile), audio_tmpdir])
    m3u_relativized = m3u_tmpfile + '.rel'

    in_fh = open(m3u_tmpfile, 'r')
    out_fh = open(m3u_relativized, 'w')

    relativize_m3u(basedir, in_fh, out_fh)

    in_fh.close()
    out_fh.close()

    with open(m3u_relativized, "r") as fh:
        for line in fh:
            m = re.match('^([^#].*)$', line)
            if m:
                path = m.group(1)
                assert not os.path.isabs(path)
                assert os.path.isfile(os.path.join(basedir, path))
                
    os.remove(m3u_relativized)
