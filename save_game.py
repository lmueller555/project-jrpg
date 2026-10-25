"""Bounded JSON save files with atomic replacement and nonfatal I/O errors."""
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile


MAX_SAVE_BYTES = 1024 * 1024


class SaveStore:
    """Store an envelope whose game-specific validation belongs to the caller.

    A ``None`` path disables disk access, which is useful for headless games and
    tests. An unsuccessful write leaves the previous save intact.
    """

    def __init__(self, path=None):
        self.path = Path(path) if path is not None else None
        self.error = None

    @property
    def enabled(self):
        return self.path is not None

    def load(self):
        self.error = None
        if not self.enabled:
            return None
        try:
            with self.path.open('rb') as saved:
                raw = saved.read(MAX_SAVE_BYTES + 1)
            if len(raw) > MAX_SAVE_BYTES:
                self.error = 'The saved journey is too large to read.'
                return None
            payload = json.loads(raw.decode('utf-8'))
            if not isinstance(payload, dict):
                self.error = 'The saved journey has an invalid format.'
                return None
            return payload
        except FileNotFoundError:
            return None
        except (OSError, UnicodeError, ValueError, RecursionError):
            self.error = 'The saved journey could not be read.'
            return None

    def write(self, payload):
        self.error = None
        if not self.enabled:
            return False
        temporary = None
        try:
            if not isinstance(payload, dict):
                self.error = 'The journey could not be saved: invalid format.'
                return False
            raw = (json.dumps(payload, ensure_ascii=False, allow_nan=False,
                              indent=2) + '\n').encode('utf-8')
            if len(raw) > MAX_SAVE_BYTES:
                self.error = 'The journey is too large to save.'
                return False
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                    mode='wb', dir=self.path.parent,
                    prefix=f'.{self.path.name}.', suffix='.tmp', delete=False) as saved:
                temporary = Path(saved.name)
                saved.write(raw)
                saved.flush()
                os.fsync(saved.fileno())
            os.replace(temporary, self.path)
            temporary = None
            return True
        except (OSError, UnicodeError, TypeError, ValueError, RecursionError):
            self.error = 'The journey could not be saved.'
            return False
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    # An unwritable directory can also prevent cleanup; it
                    # must never turn an I/O failure into a game crash.
                    pass
