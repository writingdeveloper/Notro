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
import threading
import time
import uuid

SUPPORTED_EXTS = (".png", ".gif", ".webp")
SCHEMA_VERSION = 1

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# fetch.py가 다운로드/복사 중 assets 루트에 남기는 임시 파일 접두사 — 자동 인식
# 대상에서 제외한다.
_TEMP_PREFIXES = ("_dl", "_cp", "_pb")

# APNG는 IHDR 직후 acTL, 애니메이션 WebP는 VP8X 직후 ANIM 청크를 갖는다.
# PIL 없이 헤더만 읽어 애니메이션 여부를 판정한다 (폴더 스캔은 매 표시마다
# 수십~수백 파일을 훑으므로 디코딩 비용을 피한다).
_ANIM_MARKERS = {".png": b"acTL", ".webp": b"ANIM"}


def _now() -> float:
    return time.time()


def file_is_animated(path: str) -> bool:
    """확장자 + 헤더 스니핑으로 애니메이션 여부 판정 (실패 시 False)."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".gif":
        return True
    marker = _ANIM_MARKERS.get(ext)
    if not marker:
        return False
    try:
        with open(path, "rb") as f:
            head = f.read(65536)
    except OSError:
        return False
    return marker in head


# ---------- 한글 초성 검색 ----------
# 한글 음절(가~힣)은 (초성×588 + 중성×28 + 종성) 구조라 나눗셈 한 번으로 초성이
# 나온다. 사용자가 "ㅁㅋ"만 쳐도 "미쿠"가 걸리게 하려는 것 — 한국어 사용자에게는
# 이름 전체를 치는 것보다 이쪽이 훨씬 빠르다.
_CHOSEONG = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
_SYLLABLE_FIRST, _SYLLABLE_LAST = 0xAC00, 0xD7A3
_JAMO_FIRST, _JAMO_LAST = 0x3131, 0x314E  # 호환 자모 ㄱ~ㅎ (IME가 넣는 낱자)


def to_choseong(text: str) -> str:
    """한글 음절을 초성으로 바꾼 소문자 문자열 (그 외 문자는 그대로)."""
    out = []
    for ch in text.lower():
        code = ord(ch)
        if _SYLLABLE_FIRST <= code <= _SYLLABLE_LAST:
            out.append(_CHOSEONG[(code - _SYLLABLE_FIRST) // 588])
        else:
            out.append(ch)
    return "".join(out)


def has_jamo(text: str) -> bool:
    return any(_JAMO_FIRST <= ord(c) <= _JAMO_LAST for c in text)


def matches_query(query: str, name: str, keywords) -> bool:
    """이름·키워드 부분일치. 낱자가 섞인 질의는 초성 검색으로 한 번 더 본다.

    초성 검색은 **일반 일치가 실패했을 때만** 적용한다 — 질의에 낱자가 없으면
    (영문·완성형 한글) 예전과 정확히 같게 동작한다.
    """
    q = (query or "").strip().lower()
    if not q:
        return True
    fields = [(name or "").lower()] + [str(k).lower() for k in (keywords or [])]
    if any(q in f for f in fields):
        return True
    if not has_jamo(q):
        return False
    # 질의의 완성형 음절도 초성으로 낮춰 비교한다 — IME 조합 중인 "ㅁ쿠" 같은
    # 중간 상태에서도 "미쿠"가 계속 걸린다.
    cq = to_choseong(q)
    return any(cq in to_choseong(f) for f in fields)


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
        self._asset_scan_cache: dict[str, tuple[tuple, list[dict]]] = {}
        # 자산 HTTP 서버(다중 요청 스레드)와 피커 js_api 스레드가 항목·폴더·
        # 스캔 캐시에 동시 접근하므로, 순회 중 변경으로 인한 오류(RuntimeError:
        # dictionary changed size 등)를 막기 위해 재진입 락으로 상태 접근을 보호한다.
        self._lock = threading.RLock()
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
            i.setdefault("content_hash", "")
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
                 favorite=False, collection="", content_hash="") -> dict:
        item = {
            "id": uuid.uuid4().hex[:12], "type": type_, "name": name,
            "keywords": list(keywords or []), "source_kind": source_kind,
            "source_url": source_url, "filename": filename,
            "animated": bool(animated), "convert_warning": bool(convert_warning),
            "favorite": bool(favorite), "collection": collection or "",
            "content_hash": content_hash or "",
            "added_at": _now(), "use_count": 0, "last_used": 0,
        }
        with self._lock:
            self._items[item["id"]] = item
            try:
                self._save()
            except Exception:
                self._items.pop(item["id"], None)
                raise
        return item

    def find_by_content_hash(self, content_hash: str, type_: str,
                             collection: str) -> dict | None:
        """같은 타입·컬렉션에 저장된 동일 바이트 항목을 찾는다."""
        with self._lock:
            return next((i for i in self._items.values()
                         if i.get("content_hash") == content_hash
                         and i["type"] == type_
                         and i.get("collection", "") == collection), None)

    def get(self, item_id: str) -> dict | None:
        return self._items.get(item_id)

    def remove_item(self, item_id: str) -> None:
        with self._lock:
            item = self._items.pop(item_id, None)
            if item:
                try:
                    os.remove(self.asset_path(item))
                except OSError:
                    pass
                self._save()

    def touch(self, item_id: str) -> None:
        with self._lock:
            item = self._items.get(item_id)
            if not item:
                return  # 폴더 항목 등은 무시
            item["use_count"] += 1
            item["last_used"] = _now()
            self._save()

    def toggle_favorite(self, item_id: str) -> bool:
        """등록 항목의 즐겨찾기를 반전하고 새 값을 반환 (폴더 항목은 무시→False)."""
        with self._lock:
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
        with self._lock:
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
        """세로 바용 컬렉션 목록: 등록 항목의 collection(빈 값 제외) + 감시 폴더
        basename + assets\\ 하위에서 자동 인식된 폴더명."""
        with self._lock:
            regs = {i.get("collection", "") for i in self._items.values()}
            folders = {os.path.basename(f["path"]) for f in self._folders}
        scanned = {i["collection"] for i in self.scan_asset_dirs()}
        regs.discard("")
        scanned.discard("")
        return sorted(regs | folders | scanned)

    def collection_icon(self, name: str) -> str | None:
        """세로 바 대표 아이콘용 첫 항목 id. 등록 항목을 먼저, 그다음 감시
        폴더 스캔 항목 순으로 찾는다(all_display_items() 순서). 없으면 None."""
        for i in self.all_display_items():
            if (i.get("collection") or "") == name:
                return i["id"]
        return None

    def items(self) -> list[dict]:
        with self._lock:
            return sorted(self._items.values(), key=lambda i: i["name"].lower())

    def recent(self, limit: int = 16) -> list[dict]:
        with self._lock:
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
        with self._lock:
            if any(f["path"] == ap for f in self._folders):
                return
            self._folders.append({"path": ap, "default_type": default_type})
            self._save()

    def remove_folder(self, path: str) -> None:
        ap = os.path.abspath(path)
        with self._lock:
            self._folders = [f for f in self._folders if f["path"] != ap]
            self._scan_cache.pop(ap, None)
            self._save()

    def folders(self) -> list[dict]:
        with self._lock:
            return list(self._folders)

    def scan_folders(self) -> list[dict]:
        with self._lock:
            folders = list(self._folders)  # 순회 중 변경 방지 스냅샷
        out: list[dict] = []
        for folder in folders:
            path, dtype = folder["path"], folder["default_type"]
            try:
                entries = sorted(os.listdir(path))
            except OSError:
                continue  # 소실 폴더는 건너뜀 (UI 회색 처리는 folders()의 exists로)
            names = [n for n in entries
                     if os.path.splitext(n)[1].lower() in SUPPORTED_EXTS]
            sig = (self._dir_sig(path), tuple(names))
            with self._lock:
                cached = self._scan_cache.get(path)
            if cached and cached[0] == sig:
                out.extend(cached[1])
                continue
            items = [self._scan_item(path, n, dtype, os.path.basename(path))
                     for n in names]
            with self._lock:
                self._scan_cache[path] = (sig, items)
            out.extend(items)
        return out

    @staticmethod
    def _scan_item(dir_path: str, name: str, type_: str | None,
                   collection: str) -> dict:
        """스캔 항목 dict. type_이 None이면 애니메이션 여부로 탭을 추정한다
        (움직이는 파일 → gif 탭, 정지 → emoji 탭)."""
        ap = os.path.join(dir_path, name)
        animated = file_is_animated(ap)
        return {
            "id": "folder:" + ap, "type": type_ or ("gif" if animated else "emoji"),
            "name": os.path.splitext(name)[0],
            "keywords": [], "source_kind": "folder", "source_url": "",
            "filename": name, "abs_path": ap, "animated": animated,
            "collection": collection,
            "added_at": 0, "use_count": 0, "last_used": 0,
        }

    # ---------- assets 하위 자동 인식 ----------
    def _owned_filenames(self) -> dict[str, set[str]]:
        """폴더 slug -> 등록 항목이 소유한 파일명 집합 (중복 표시 방지용)."""
        owned: dict[str, set[str]] = {}
        with self._lock:
            for i in self._items.values():
                owned.setdefault(_slug(i.get("collection", "")),
                                 set()).add(i["filename"])
        return owned

    def _asset_scan_dirs(self) -> list[str]:
        """스캔 대상: assets 루트 + 감시 폴더로 등록되지 않은 모든 하위 폴더."""
        with self._lock:
            watched = {os.path.normcase(f["path"]) for f in self._folders}
        dirs = [self.assets_dir]
        try:
            entries = sorted(os.listdir(self.assets_dir))
        except OSError:
            return []
        for n in entries:
            p = os.path.join(self.assets_dir, n)
            if os.path.isdir(p) and os.path.normcase(p) not in watched:
                dirs.append(p)
        return dirs

    def scan_asset_dirs(self) -> list[dict]:
        """사용자가 assets\\ 아래에 직접 만든 폴더·넣은 파일을 등록 없이 표시한다.

        등록 항목이 소유한 파일은 제외하므로 기존 컬렉션 폴더에 파일을 하나
        떨어뜨려도 중복 없이 그 파일만 추가로 보인다. 폴더명이 곧 컬렉션명이며
        `_uncategorized`와 루트는 미분류로 취급한다.
        """
        out: list[dict] = []
        owned = self._owned_filenames()
        for d in self._asset_scan_dirs():
            root = os.path.normcase(d) == os.path.normcase(self.assets_dir)
            base = os.path.basename(d)
            collection = "" if root or base == "_uncategorized" else base
            skip = set() if root else owned.get(_slug(collection), set())
            try:
                entries = sorted(os.listdir(d))
            except OSError:
                continue
            names = [n for n in entries
                     if os.path.splitext(n)[1].lower() in SUPPORTED_EXTS
                     and n not in skip
                     and not n.startswith(_TEMP_PREFIXES)]
            sig = (self._dir_sig(d), tuple(names))
            with self._lock:
                cached = self._asset_scan_cache.get(d)
            if cached and cached[0] == sig:
                out.extend(cached[1])
                continue
            items = [self._scan_item(d, n, None, collection) for n in names]
            with self._lock:
                self._asset_scan_cache[d] = (sig, items)
            out.extend(items)
        return out

    @staticmethod
    def _dir_sig(path: str) -> float:
        try:
            return os.stat(path).st_mtime_ns
        except OSError:
            return 0

    def all_display_items(self) -> list[dict]:
        return self.items() + self.scan_folders() + self.scan_asset_dirs()

    def resolve(self, item_id: str) -> dict | None:
        """등록 항목 우선, 없으면 스캔 항목(감시 폴더 + assets 자동 인식)에서 조회."""
        item = self._items.get(item_id)
        if item is None and item_id.startswith("folder:"):
            item = next((i for i in self.scan_folders() + self.scan_asset_dirs()
                         if i["id"] == item_id), None)
        return item

    # ---------- 검색 ----------
    # 정식 검색 책임(스펙 §3)은 여기 있다. 프런트엔드 app.js filtered()는
    # 타이핑 반응성을 위한 동일 규칙의 미러일 뿐이다.
    def search(self, query: str, type_: str | None = None) -> list[dict]:
        """이름·키워드 대소문자 무시 부분일치(+한글 초성). 빈 쿼리면 type_만 적용."""
        items = self.all_display_items()
        if type_ is not None:
            items = [i for i in items if i["type"] == type_]
        if not (query or "").strip():
            return items
        return [i for i in items
                if matches_query(query, i["name"], i["keywords"])]
