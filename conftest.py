"""
Pytest configuration.

Em ambientes sem backend de áudio (headless/CI), o import do `sounddevice`
falha na inicialização do PortAudio. Injetamos um stub leve apenas quando o
import real falha, para que os módulos possam ser coletados e testados.
Em máquinas com áudio (homelab), o sounddevice real é usado normalmente.
"""
import sys
import types

try:
    import sounddevice  # noqa: F401
except Exception:  # pragma: no cover - somente headless sem áudio
    fake = types.ModuleType("sounddevice")
    fake.query_devices = lambda: []

    class _Stream:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def start(self):
            pass

        def stop(self):
            pass

        def close(self):
            pass

        def write(self, *args):
            pass

    fake.InputStream = _Stream
    fake.RawOutputStream = _Stream
    fake.play = lambda *args, **kwargs: None
    fake.wait = lambda *args, **kwargs: None

    sys.modules["sounddevice"] = fake
