# -*- coding: utf-8 -*-
"""Portable, explicitly user-initiated Notro emoji/sticker/GIF packs.

No account tokens, Discord URLs, device paths, auto-captured private screenshots,
or clipboard history are exported. Only user-registered media, metadata and
content hashes are included. Never extract a caller-controlled zip path.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import zipfile
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from . import fetch
from .capture_store import CAPTURE_COLLECTION_ID

FORMAT = "notro-media-pack"
VERSION = 1
MAX_ITEMS = 1500
MAX_ITEM_SIZE = 20 * 1024 * 1024
MAX_TOTAL_SIZE = 180 * 1024 * 1024
MAX_MANIFEST_SIZE = 2 * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000
EXTENSIONS = {".png", ".gif", ".webp", ".jpg", ".jpeg"}
KINDS = {"emoji", "sticker", "gif"}
PATH_RE = re.compile(r"assets/[0-9]{5}\.(?:png|gif|webp|jpg|jpeg)\Z")
SHA_RE = re.compile(r"[a-f0-9]{64}\Z")
FORMATS = {
    ".png": "PNG", ".gif": "GIF", ".webp": "WEBP",
    ".jpg": "JPEG", ".jpeg": "JPEG",
}


class PackError(ValueError):
    """Bad or unsafe pack; no assets are imported until preflight passes."""


def _digest_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _check_meta(item: dict) -> dict:
    if not isinstance(item, dict):
        raise PackError("bad item metadata")
    name = item.get("name")
    kind = item.get("type")
    collection = item.get("collection", "")
    keywords = item.get("keywords", [])
    if not isinstance(name, str) or not name.strip() or len(name) > 160:
        raise PackError("bad item name")
    if kind not in KINDS:
        raise PackError("bad item kind")
    if not isinstance(collection, str) or len(collection) > 80:
        raise PackError("bad collection")
    # Library._slug("..") would name the parent directory on Windows.
    if collection.strip().strip(".") == "" and collection.strip():
        raise PackError("unsafe collection")
    if not isinstance(keywords, list) or len(keywords) > 32:
        raise PackError("bad keywords")
    if not all(isinstance(k, str) and len(k) <= 80 for k in keywords):
        raise PackError("bad keyword")
    return {
        "name": name.strip(), "type": kind, "collection": collection.strip(),
        "keywords": list(keywords),
    }


def export_pack(library, destination: str) -> dict:
    """Atomic ZIP export of registered items, excluding private Captures."""
    dest = Path(destination)
    if dest.suffix.lower() != ".zip":
        raise PackError("pack filename must end in .zip")
    items = [item for item in library.items()
             if item.get("collection") != CAPTURE_COLLECTION_ID]
    if len(items) > MAX_ITEMS:
        raise PackError("too many items")
    manifest = []
    payloads = []
    total = 0
    for item in items:
        meta = _check_meta(item)
        src = Path(library.asset_path(item))
        ext = src.suffix.lower()
        if ext not in EXTENSIONS or not src.is_file():
            raise PackError(f"missing or unsupported asset: {item['name']}")
        size = src.stat().st_size
        if size > MAX_ITEM_SIZE or total + size > MAX_TOTAL_SIZE:
            raise PackError("pack is too large")
        total += size
        arc = f"assets/{len(manifest)+1:05d}{ext}"
        manifest.append({**meta, "file": arc, "sha256": _digest_file(str(src))})
        payloads.append((src, arc))
    data = json.dumps({
        "format": FORMAT, "version": VERSION, "items": manifest,
    }, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(data) > MAX_MANIFEST_SIZE:
        raise PackError("pack manifest too large")
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix="notro-pack-", suffix=".zip", dir=dest.parent)
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("manifest.json", data)
            for src, arc in payloads:
                z.write(src, arcname=arc)
        os.replace(tmp, dest)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return {"count": len(manifest), "bytes": total, "path": str(dest)}


def import_pack(library, archive: str) -> dict:
    """Validate entire ZIP before mutating the library; merge duplicates safely."""
    path = Path(archive)
    if path.suffix.lower() != ".zip" or not path.is_file():
        raise PackError("not a ZIP media pack")
    records = []
    with zipfile.ZipFile(path, "r") as z:
        infos = z.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)) or len(names) > MAX_ITEMS + 1:
            raise PackError("invalid ZIP members")
        if "manifest.json" not in names:
            raise PackError("manifest is missing")
        if any(name != "manifest.json" and not PATH_RE.fullmatch(name) for name in names):
            raise PackError("unrecognized ZIP path")
        if any(info.flag_bits & 1 for info in infos):
            raise PackError("encrypted ZIP files are unsupported")
        by_name = {info.filename: info for info in infos}
        if by_name["manifest.json"].file_size > MAX_MANIFEST_SIZE:
            raise PackError("manifest too large")
        manifest_bytes = z.read("manifest.json")
        if len(manifest_bytes) > MAX_MANIFEST_SIZE:
            raise PackError("manifest too large")
        try:
            manifest = json.loads(manifest_bytes)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PackError("invalid manifest") from exc
        if (not isinstance(manifest, dict)
                or manifest.get("format") != FORMAT
                or manifest.get("version") != VERSION):
            raise PackError("unsupported pack format/version")
        items = manifest.get("items")
        if not isinstance(items, list) or len(items) > MAX_ITEMS:
            raise PackError("too many items")
        declared = set()
        total = 0
        for entry in items:
            meta = _check_meta(entry)
            filename = entry.get("file")
            expected = entry.get("sha256")
            if (not isinstance(filename, str) or not PATH_RE.fullmatch(filename)
                    or filename not in by_name or filename in declared
                    or not isinstance(expected, str) or not SHA_RE.fullmatch(expected)):
                raise PackError("invalid media entry")
            declared.add(filename)
            info = by_name[filename]
            total += info.file_size
            if info.file_size > MAX_ITEM_SIZE or total > MAX_TOTAL_SIZE:
                raise PackError("pack exceeds allowed size")
            records.append((filename, expected, meta))
        if set(names) != declared | {"manifest.json"}:
            raise PackError("unexpected extra media")
        # All decompression and content checks happen before library writes.
        with tempfile.TemporaryDirectory(prefix="notro-import-") as scratch:
            checked = []
            for n, (filename, expected, meta) in enumerate(records):
                dest = Path(scratch) / f"asset-{n:05d}{Path(filename).suffix.lower()}"
                digest = hashlib.sha256()
                received = 0
                with z.open(filename) as source, open(dest, "wb") as out:
                    while True:
                        part = source.read(65536)
                        if not part:
                            break
                        received += len(part)
                        if received > MAX_ITEM_SIZE:
                            raise PackError("decompressed asset too large")
                        digest.update(part)
                        out.write(part)
                if received != by_name[filename].file_size or digest.hexdigest() != expected:
                    raise PackError("asset SHA-256 mismatch")
                try:
                    with Image.open(dest) as image:
                        if (image.format != FORMATS[dest.suffix.lower()]
                                or image.width * image.height > MAX_IMAGE_PIXELS):
                            raise PackError("invalid/oversized image")
                        image.verify()
                except (OSError, UnidentifiedImageError) as exc:
                    raise PackError("invalid image content") from exc
                checked.append((str(dest), meta))
            added = duplicate = failed = 0
            for dest, meta in checked:
                try:
                    fetch.register_from_file(
                        library, dest, meta["type"], name=meta["name"],
                        keywords=meta["keywords"], collection=meta["collection"])
                    added += 1
                except fetch.DuplicateAssetError:
                    duplicate += 1
                except Exception:
                    failed += 1
            return {"added": added, "duplicate": duplicate, "failed": failed}
