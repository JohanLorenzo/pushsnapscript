import contextlib
import pytest
import os
import tempfile

from unittest.mock import MagicMock

from pushsnapscript.snap_store import snapcraft_store_client, push, _craft_credentials_file

SNAPCRAFT_SAMPLE_CONFIG = '''[login.ubuntu.com]
macaroon = SomeBase64
unbound_discharge = SomeOtherBase64
email = release@m.c
'''


@pytest.mark.parametrize('channel', ('beta', 'candidate'))
def test_push(monkeypatch, channel):
    call_count = (n for n in range(0, 2))

    context = MagicMock()

    with tempfile.NamedTemporaryFile('w+') as macaroon:
        context.config = {
            'macaroons_locations': {channel: macaroon.name}
        }
        macaroon.write(SNAPCRAFT_SAMPLE_CONFIG)

        with tempfile.TemporaryDirectory() as temp_dir:
            def snapcraft_store_client_push_fake(snap_file_path, channel):
                # This function can't be a regular mock because of the following check:
                assert os.getcwd() == temp_dir     # Push must be done from a disposable dir

                assert snap_file_path == '/some/file.snap'
                assert channel == channel
                next(call_count)

            @contextlib.contextmanager
            def TemporaryDirectory():
                try:
                    yield temp_dir
                finally:
                    pass

            monkeypatch.setattr(tempfile, 'TemporaryDirectory', TemporaryDirectory)
            monkeypatch.setattr(snapcraft_store_client, 'push', snapcraft_store_client_push_fake)
            push(context, '/some/file.snap', channel)

            assert os.getcwd() != temp_dir
            snapcraft_cred_file = os.path.join(temp_dir, '.snapcraft', 'snapcraft.cfg')

    assert not os.path.exists(snapcraft_cred_file)
    assert next(call_count) == 1


def test_push_early_return_if_not_allowed(monkeypatch):
    call_count = (n for n in range(0, 2))

    context = MagicMock()

    def increase_call_count(_, __):
        next(call_count)

    monkeypatch.setattr(snapcraft_store_client, 'push', increase_call_count)
    push(context, '/some/file.snap', channel='mock')

    assert next(call_count) == 0


@pytest.mark.parametrize('channel', ('beta', 'candidate'))
def test_craft_credentials_file(channel):
    context = MagicMock()

    with tempfile.NamedTemporaryFile('w+') as macaroon:
        context.config = {
            'macaroons_locations': {channel: macaroon.name}
        }
        macaroon.write(SNAPCRAFT_SAMPLE_CONFIG)
        macaroon.seek(0)

        with tempfile.TemporaryDirectory() as temp_dir:
            _craft_credentials_file(context, channel, temp_dir)
            with open(os.path.join(temp_dir, '.snapcraft', 'snapcraft.cfg')) as f:
                assert f.read() == SNAPCRAFT_SAMPLE_CONFIG
