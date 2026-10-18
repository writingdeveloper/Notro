# -*- coding: utf-8 -*-
"""User-initiated portable Notro preferences backup.

This JSON is NOT a media pack and never contains clipboard images, Captures,
Discord URLs, authentication data, or user media bytes. Watched absolute
folder paths are exported only with explicit opt-in. Import is two-stage:
validate/preview, then explicit restore; never auto-enable auto-send, capture
or Windows startup. Nothing contacts Discord or embeds REA.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

from . import config

FORMAT = "notro-settings"
VERSION = 1
MAX_BYTES = 128 * 1024
MAX_FOLDERS = 64
MAX_PATH_LENGTH = 2048

# Restore only known public preferences. Startup, telemetry and any future
# secrets/keys are deliberately omitted from this allowlist.
INT_DEFAULTS = {
    "limit_mb": 20,
    "auto_update": 1,
    "picker_w": 500,
    "picker_h": 420,
    "paste_px_emoji": 48,
    "paste_px_sticker": 160,
    "paste_px_gif": 0,
}
STRING_DEFAULTS = {
    "lang": "auto",
    "hotkey": "ctrl+shift+e",
}
SAFE_BOOLEANS = ("auto_send", "auto_capture_save")
INT_RANGES = {
    "limit_mb": (10, 1024),
    "auto_update": (0, 1),
    "picker_w": (360, 3840),
    "picker_h": (300, 2160),
    "paste_px_emoji": (0, 512),
    "paste_px_sticker": (0, 512),
    "paste_px_gif": (0, 512),
}
LANGS = {"auto", "en", "ko", "ja", "zh", "es"}


class SettingsBackupError(ValueError):
    """Invalid/unsupported settings backup, safe to report without its data."""


def _valid_setting(key: str, value) -> bool:
    if key in INT_RANGES:
        low, high = INT_RANGES[key]
        return type(value) is int and low <= value <= high
    if key == "lang":
        return type(value) is str and value in LANGS
    if key == "hotkey":
        # Import from only the user's available hotkey choices (incl. off).
        from .hotkey import HOTKEY_CHOICES, HOTKEY_OFF

        return type(value) is str and value in set(HOTKEY_CHOICES) | {HOTKEY_OFF}
    if key in SAFE_BOOLEANS:
        return type(value) is bool
    return False


def _settings_snapshot() -> dict:
    values = {
        k: config.get_setting_int(k, default)
        for k, default in INT_DEFAULTS.items()
    }
    values.update({
        k: config.get_setting_str(k, default)
        for k, default in STRING_DEFAULTS.items()
    })
    values.update({
        k: config.get_setting_flag(k)
        for k in SAFE_BOOLEANS
    })
    return values


def _check_document(data: object) -> dict:
    if not isinstance(data, dict) or set(data) != {
            "format", "version", "settings", "watched_folders"}:
        raise SettingsBackupError("invalid_schema")
    if data["format"] != FORMAT or data["version"] != VERSION:
        raise SettingsBackupError("unsupported_version")
    settings = data["settings"]
    if (not isinstance(settings, dict) or
            not settings or
            not set(settings) <= set(INT_DEFAULTS) | set(STRING_DEFAULTS) |
            set(SAFE_BOOLEANS)):
        raise SettingsBackupError("invalid_settings")
    for key, value in settings.items():
        if not _valid_setting(key, value):
            raise SettingsBackupError("invalid_settings")

    folders = data["watched_folders"]
    if not isinstance(folders, list) or len(folders) > MAX_FOLDERS:
        raise SettingsBackupError("invalid_folders")
    checked = []
    paths = set()
    for folder in folders:
        if not isinstance(folder, dict) or set(folder) != {"path", "default_type"}:
            raise SettingsBackupError("invalid_folders")
        path, kind = folder["path"], folder["default_type"]
        if (not isinstance(path, str) or not path or len(path) > MAX_PATH_LENGTH
                or chr(0) in path or not os.path.isabs(path)
                or not isinstance(kind, str)
                or kind not in {"emoji", "sticker", "gif"}):
            raise SettingsBackupError("invalid_folders")
        key = os.path.normcase(os.path.normpath(path))
        if key in paths:
            raise SettingsBackupError("invalid_folders")
        paths.add(key)
        checked.append({"path": path, "default_type": kind})

    # Never trust another backup to enable message sending or capture.
    # Import preflight retains the user's original boolean values only
    # for preview disclosure; applying below forces these safety flags OFF.
    return {"settings": dict(settings), "watched_folders": checked}


def export_settings(library, destination: str, *, include_folders: bool = False,
                    snapshot: dict | None = None) -> dict:
    """Atomically save whitelisted settings; folder paths are opt-in."""
    dest = Path(destination)
    if dest.suffix.lower() != ".json":
        raise SettingsBackupError("must_be_json")
    folders = library.folders() if include_folders else []
    doc = {
        "format": FORMAT, "version": VERSION,
        "settings": snapshot if snapshot is not None else _settings_snapshot(),
        "watched_folders": folders,
    }
    safe = _check_document(doc)
    doc["settings"] = safe["settings"]
    doc["watched_folders"] = safe["watched_folders"]
    raw = json.dumps(doc, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    if len(raw) > MAX_BYTES:
        raise SettingsBackupError("too_large")
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="notro-settings-", suffix=".tmp", dir=dest.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, dest)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return {"settings_count": len(doc["settings"]),
            "folders_count": len(doc["watched_folders"]), "path": str(dest)}


def preview_settings(source: str) -> tuple[dict, str]:
    """Read+validate small JSON without changing config, paths, or library."""
    path = Path(source)
    if path.suffix.lower() != ".json" or not path.is_file():
        raise SettingsBackupError("must_be_json")
    if path.stat().st_size > MAX_BYTES:
        raise SettingsBackupError("too_large")
    with path.open("rb") as f:
        raw = f.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise SettingsBackupError("too_large")
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SettingsBackupError("invalid_json") from exc
    return _check_document(doc), hashlib.sha256(raw).hexdigest()


def apply_settings(doc: dict, library, *, restore_folders: bool = False,
                   write_int=None, write_str=None) -> dict:
    """Apply an already reviewed, validated profile. Call only on explicit UI consent.

    Import is additive for watched folders (never deletes old folders or
    reads any images). Missing external directories remain omitted.
    Auto-send, auto-capture and startup are never enabled by restoration.
    Settings affecting the app/tray/hotkey require a restart to take effect.
    """
    safe = _check_document({
        "format": FORMAT, "version": VERSION,
        "settings": doc["settings"], "watched_folders": doc["watched_folders"],
    })
    write_int = write_int or config.set_setting_int
    write_str = write_str or config.set_setting_str
    # Existing app media and private Captures are left untouched. All
    # externally supplied values were preflight-validated above.
    applied = 0
    for key, val in safe["settings"].items():
        if key in SAFE_BOOLEANS:
            # Dangerous capabilities are explicitly disabled, not restored.
            continue
        if key in INT_DEFAULTS:
            write_int(key, val)
        else:
            write_str(key, val)
        applied += 1
    for flag in SAFE_BOOLEANS:
        write_int(flag, 0)

    added = missing = 0
    if restore_folders:
        previous = {
            os.path.normcase(os.path.normpath(f["path"]))
            for f in library.folders()
        }
        for entry in safe["watched_folders"]:
            path = entry["path"]
            if not os.path.isdir(path):
                missing += 1
                continue
            norm = os.path.normcase(os.path.normpath(path))
            if norm not in previous:
                library.add_folder(path, entry["default_type"])
                previous.add(norm)
                added += 1
    return {"applied": applied, "folders_added": added,
            "folders_missing": missing, "restart_required": applied > 0}
