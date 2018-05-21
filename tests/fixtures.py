import os
import pytest
import tempfile
import shutil

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')

@pytest.fixture(scope='function')
def pls_tmpfile():
    tmpfile = tempfile.NamedTemporaryFile(suffix='.pls', delete=False).name
    yield tmpfile
    os.remove(tmpfile)

@pytest.fixture(scope='function')
def m3u_tmpfile():
    tmpfile = tempfile.NamedTemporaryFile(suffix='.m3u', delete=False).name
    yield tmpfile
    os.remove(tmpfile)

@pytest.fixture(scope='function')
def audio_tmpdir():
    audio_dir = os.path.join(FIXTURE_DIR, 'audio')
    tmpdir = tempfile.mkdtemp()
    audio_tmpdir = os.path.join(tmpdir, 'audio')
    shutil.copytree(audio_dir, audio_tmpdir)
    yield audio_tmpdir
    shutil.rmtree(tmpdir)
