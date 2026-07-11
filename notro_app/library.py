# -*- coding: utf-8 -*-
"""피커 라이브러리: 항목/폴더 JSON 영속 + 자산 캐시.

항목 dict 키: id, type(emoji|sticker|gif), name, keywords[], source_kind
(discord-cdn|local|folder), source_url, filename, animated, added_at,
use_count, last_used. 폴더 스캔 항목은 abs_path가 추가되고 영속되지 않는다.
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid

SUPPORTED_EXTS = (".png", ".gif", ".webp")
SCHEMA_VERSION = 1

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _now() -> float:
    return time.time()


def _slug(name) -> str:
    """컬렉션명을 파일시스템 안전 폴더명으로. 빈 값은 미분류 폴더."""
    name = (name or "").strip()
    if not name:
        return "_uncategorized"
    return _INVALID_CHARS.sub("_", name)[:80] or "_uncategorized"


class Library:
    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.assets_dir = os.path.join(data_dir, "assets")
        os.makedirs(self.assets_dir, exist_ok=True)
        self._items: dict[str, dict] = {}
        self._folders: list[dict] = []
        self._scan_cache: dict[str, tuple[tuple, list[dict]]] = {}
        self._load()

    # ---------- 영속 ----------
    def _lib_path(self) -> str:
        return os.path.join(self.data_dir, "library.json")

    def _folders_path(self) -> str:
        return os.path.join(self.data_dir, "folders.json")

    def _load(self) -> None:
        self._items = {}
        self._folders = []
        for path, apply in ((self._lib_path(), self._apply_lib),
                            (self._folders_path(), self._apply_folders)):
            if not os.path.exists(path):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    apply(json.load(f))
            except (json.JSONDecodeError, OSError, KeyError, TypeError):
                try:  # 손상 파일은 백업하고 빈 상태로 시작
                    os.replace(path, path + ".bak")
                except OSError:
                    pass
        self._migrate_flat_assets_to_folders()

    def _migrate_flat_assets_to_folders(self) -> None:
        """v2.4 이전 평면 저장 자산을 컬렉션별 하위 폴더로 1회 이전한다.
        이미 이전됐으면(평면 위치에 파일 없음) 조용히 스킵 — 멱등."""
        for item in self._items.values():
            flat = os.path.join(self.assets_dir, item["filename"])
            if not os.path.exists(flat):
                continue
            target = self.asset_path(item)
            if os.path.normpath(target) == os.path.normpath(flat):
                continue
            try:
                os.makedirs(os.path.dirname(target), exist_ok=True)
                os.replace(flat, target)
            except OSError:
                pass

    def _apply_lib(self, data: dict) -> None:
        items = {}
        for i in data.get("items", []):
            i.setdefault("convert_warning", False)  # 구버전 항목 하위호환
            i.setdefault("favorite", False)
            i.setdefault("collection", "")
            items[i["id"]] = i
        self._items = items

    def _apply_folders(self, data: dict) -> None:
        self._folders = list(data.get("folders", []))

    def _save(self) -> None:
        self._atomic_write(self._lib_path(),
                           {"schema": SCHEMA_VERSION,
                            "items": list(self._items.values())})
        self._atomic_write(self._folders_path(),
                           {"schema": SCHEMA_VERSION, "folders": self._folders})

    @staticmethod
    def _atomic_write(path: str, obj: dict) -> None:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)

    # ---------- 항목 ----------
    def new_asset_filename(self, ext: str) -> str:
        return uuid.uuid4().hex[:12] + ext

    def add_item(self, type_, name, keywords, source_kind, source_url,
                 filename, animated, convert_warning=False,
                 favorite=False, collection="") -> dict:
        item = {
            "id": uuid.uuid4().hex[:12], "type": type_, "name": name,
            "keywords": list(keywords or []), "source_kind": source_kind,
            "source_url": source_url, "filename": filename,
            "animated": bool(animated), "convert_warning": bool(convert_warning),
            "favorite": bool(favorite), "collection": collection or "",
            "added_at": _now(), "use_count": 0, "last_used": 0,
        }
        self._items[item["id"]] = item
        self._save()
        return item

    def get(self, item_id: str) -> dict | None:
        return self._items.get(item_id)

    def remove_item(self, item_id: str) -> None:
        item = self._items.pop(item_id, None)
        if item:
            try:
                os.remove(self.asset_path(item))
            except OSError:
                pass
            self._save()

    def touch(self, item_id: str) -> None:
        item = self._items.get(item_id)
        if not item:
            return  # 폴더 항목 등은 무시
        item["use_count"] += 1
        item["last_used"] = _now()
        self._save()

    def toggle_favorite(self, item_id: str) -> bool:
        """등록 항목의 즐겨찾기를 반전하고 새 값을 반환 (폴더 항목은 무시→False)."""
        item = self._items.get(item_id)
        if not item:
            return False
        item["favorite"] = not item.get("favorite", False)
        self._save()
        return item["favorite"]

    def favorites(self) -> list[dict]:
        return [i for i in self.items() if i.get("favorite")]

    def set_collection(self, item_id: str, name: str) -> None:
        """등록 항목의 컬렉션을 바꾸고 파일을 새 폴더로 이동한다.
        이동이 실패하면 메타데이터도 바꾸지 않는다(파일 위치와 collection
        필드의 불일치를 방지 — asset_path()는 collection 필드를 그대로 믿는다)."""
        item = self._items.get(item_id)
        if item is None:
            return
        new_name = (name or "").strip()
        if new_name == item.get("collection", ""):
            return
        old_path = self.asset_path(item)
        new_dir = self.collection_dir(new_name)
        new_path = os.path.join(new_dir, item["filename"])
        if os.path.exists(old_path) and old_path != new_path:
            try:
                os.replace(old_path, new_path)
            except OSError:
                return
        item["collection"] = new_name
        self._save()

    def collections(self) -> list[str]:
        """세로 바용 컬렉션 목록: 등록 항목의 collection(빈 값 제외) + 감시 폴더 basename."""
        regs = {i.get("collection", "") for i in self._items.values()}
        regs.discard("")
        folders = {os.path.basename(f["path"]) for f in self._folders}
        return sorted(regs | folders)

    def collection_icon(self, name: str) -> str | None:
        """세로 바 대표 아이콘용 첫 항목 id. 등록 항목을 먼저, 그다음 감시
        폴더 스캔 항목 순으로 찾는다(all_display_items() 순서). 없으면 None."""
        for i in self.all_display_items():
            if (i.get("collection") or "") == name:
                return i["id"]
        return None

    def items(self) -> list[dict]:
        return sorted(self._items.values(), key=lambda i: i["name"].lower())

    def recent(self, limit: int = 16) -> list[dict]:
        used = [i for i in self._items.values() if i["last_used"] > 0]
        return sorted(used, key=lambda i: i["last_used"], reverse=True)[:limit]

    def asset_path(self, item: dict) -> str:
        if item.get("abs_path"):
            return item["abs_path"]
        return os.path.join(self.assets_dir, _slug(item.get("collection", "")),
                            item["filename"])

    def collection_dir(self, name: str) -> str:
        """등록 시 자산을 저장할 폴더 (없으면 생성). fetch.py가 신규 파일을
        쓸 때 사용 — asset_path()는 순수 계산이라 여기서 생성을 담당한다."""
        d = os.path.join(self.assets_dir, _slug(name))
        os.makedirs(d, exist_ok=True)
        return d

    # ---------- 폴더 ----------
    def add_folder(self, path: str, default_type: str = "gif") -> None:
        ap = os.path.abspath(path)
        if any(f["path"] == ap for f in self._folders):
            return
        self._folders.append({"path": ap, "default_type": default_type})
        self._save()

    def remove_folder(self, path: str) -> None:
        ap = os.path.abspath(path)
        self._folders = [f for f in self._folders if f["path"] != ap]
        self._scan_cache.pop(ap, None)
        self._save()

    def folders(self) -> list[dict]:
        return list(self._folders)

    def scan_folders(self) -> list[dict]:
        out: list[dict] = []
        for folder in self._folders:
            path, dtype = folder["path"], folder["default_type"]
            try:
                entries = sorted(os.listdir(path))
            except OSError:
                continue  # 소실 폴더는 건너뜀 (UI 회색 처리는 folders()의 exists로)
            names = [n for n in entries
                     if os.path.splitext(n)[1].lower() in SUPPORTED_EXTS]
            sig = (self._dir_sig(path), tuple(names))
            cached = self._scan_cache.get(path)
            if cached and cached[0] == sig:
                out.extend(cached[1])
                continue
            items = []
            for n in names:
                ap = os.path.join(path, n)
                stem, ext = os.path.splitext(n)
                items.append({
                    "id": "folder:" + ap, "type": dtype, "name": stem,
                    "keywords": [], "source_kind": "folder", "source_url": "",
                    "filename": n, "abs_path": ap,
                    "animated": ext.lower() == ".gif",
                    "collection": os.path.basename(path),
                    "added_at": 0, "use_count": 0, "last_used": 0,
                })
            self._scan_cache[path] = (sig, items)
            out.extend(items)
        return out

    @staticmethod
    def _dir_sig(path: str) -> float:
        try:
            return os.stat(path).st_mtime_ns
        except OSError:
            return 0

    def all_display_items(self) -> list[dict]:
        return self.items() + self.scan_folders()

    # ---------- 검색 ----------
    # 정식 검색 책임(스펙 §3)은 여기 있다. 프런트엔드 app.js filtered()는
    # 타이핑 반응성을 위한 동일 규칙의 미러일 뿐이다.
    def search(self, query: str, type_: str | None = None) -> list[dict]:
        """이름·키워드 대소문자 무시 부분일치. 빈 쿼리면 type_ 필터만 적용."""
        items = self.all_display_items()
        if type_ is not None:
            items = [i for i in items if i["type"] == type_]
        q = (query or "").strip().lower()
        if not q:
            return items
        return [i for i in items
                if q in i["name"].lower()
                or any(q in k.lower() for k in i["keywords"])]
