# Collection Folders + Representative Icons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `assets/` 캐시를 컬렉션별 하위 폴더로 재구성하고(기존 파일 자동 마이그레이션), 피커 세로 바에 텍스트 대신 대표 썸네일 아이콘을 표시한다.

**Architecture:** `library.py`가 `collection` 필드에서 파일 경로를 파생시키는 순수 함수(`asset_path`)와, 파일을 실제로 옮기는 부수효과 함수(`set_collection`)를 분리한다. 이동은 metadata 갱신보다 먼저 성공해야 한다. 로드 시 1회 자동 마이그레이션. `fetch.py`는 신규 등록을 `_uncategorized/`에 쓴다. UI는 컬렉션의 대표 항목 썸네일을 원형 아이콘으로 렌더한다.

**Tech Stack:** Python 표준 라이브러리(os, re). 바닐라 JS/CSS. 신규 의존성 없음.

## Global Constraints

- `collection` 필드가 유일한 source of truth. 폴더는 항상 여기서 파생 — 반대로 폴더 구조를 보고 collection을 추론하지 않는다.
- `set_collection()`은 파일 이동 성공(또는 이동 불필요) 후에만 메타데이터를 갱신한다. 실패 시 아무것도 바꾸지 않는다.
- 감시 폴더(`folders.json`, `abs_path` 항목)는 이번 변경과 완전히 무관 — 건드리지 않는다.
- 기존 pytest 79개는 `tests/test_library.py`의 `put_asset()` 헬퍼 수정만으로 회귀 없이 통과해야 한다(다른 테스트는 전부 `asset_path()` 경유).
- 마이그레이션은 멱등(같은 상태에서 여러 번 실행해도 안전).

---

### Task 1: 슬러그 + 컬렉션 디렉터리 + asset_path 하위 폴더 인지

**Files:**
- Modify: `notro_app/library.py`
- Test: `tests/test_library.py`

**Interfaces:**
- Produces: `_slug(name: str) -> str`, `Library.collection_dir(name: str) -> str`, `Library.asset_path(item)`가 등록 항목에 대해 `assets_dir/{slug}/filename` 반환.

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_library.py`에 추가

```python
def test_slug_sanitizes_and_defaults(tmp_path):
    from notro_app.library import _slug
    assert _slug("") == "_uncategorized"
    assert _slug("  ") == "_uncategorized"
    assert _slug("miku") == "miku"
    assert _slug('a/b\\c:d') == "a_b_c_d"


def test_asset_path_uses_collection_subfolder(tmp_path):
    lib = make_lib(tmp_path)
    fn = put_asset(lib, "a.png")
    item = lib.add_item("emoji", "a", [], "local", "", fn, False, collection="miku")
    path = lib.asset_path(item)
    assert os.path.normpath(path) == os.path.normpath(
        os.path.join(lib.assets_dir, "miku", fn))


def test_asset_path_uncategorized_subfolder(tmp_path):
    lib = make_lib(tmp_path)
    fn = put_asset(lib, "b.png")
    item = lib.add_item("emoji", "b", [], "local", "", fn, False)
    path = lib.asset_path(item)
    assert os.path.normpath(path) == os.path.normpath(
        os.path.join(lib.assets_dir, "_uncategorized", fn))
```

**중요**: 위 두 테스트는 `put_asset()`이 파일을 새 위치에 써야 통과한다. 같은 파일의 `put_asset()` 헬퍼(라인 15-18)를 아래로 교체:

```python
def put_asset(lib, name="a.png", collection=""):
    from notro_app.library import _slug
    d = os.path.join(lib.assets_dir, _slug(collection))
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, name)
    Image.new("RGB", (4, 4), (255, 0, 0)).save(p)
    return name
```

(기존 `put_asset(lib, "a.png")` 호출부들은 `collection` 기본값 `""`이라 그대로 동작 — `_uncategorized`에 써짐.)

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_library.py -k "slug or subfolder" -q` → FAIL

- [ ] **Step 3: 구현** — `notro_app/library.py`

파일 상단 `import` 아래에 추가:

```python
import re

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _slug(name: str | None) -> str:
    """컬렉션명을 파일시스템 안전 폴더명으로. 빈 값은 미분류 폴더."""
    name = (name or "").strip()
    if not name:
        return "_uncategorized"
    return _INVALID_CHARS.sub("_", name)[:80] or "_uncategorized"
```

`asset_path` 메서드 교체:

```python
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
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_library.py -q` → 전체 PASS (기존 테스트도 `put_asset` 경유라 함께 통과해야 함)

- [ ] **Step 5: 커밋**

```bash
git add notro_app/library.py tests/test_library.py
git commit -m "feat(library): collection-based asset subfolders (asset_path, collection_dir)"
```

---

### Task 2: set_collection이 파일을 실제로 이동

**Files:**
- Modify: `notro_app/library.py`
- Test: `tests/test_library.py`

**Interfaces:**
- Produces: `set_collection(id, name)`가 파일을 이동시키고, 이동 성공(또는 불필요) 시에만 메타데이터 갱신.

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_library.py`에 추가

```python
def test_set_collection_moves_file_on_disk(tmp_path):
    lib = make_lib(tmp_path)
    fn = put_asset(lib, "a.png")  # _uncategorized에 생성
    item = lib.add_item("emoji", "a", [], "local", "", fn, False)
    old_path = lib.asset_path(item)
    assert os.path.exists(old_path)

    lib.set_collection(item["id"], "miku")

    new_path = lib.asset_path(lib.get(item["id"]))
    assert not os.path.exists(old_path)
    assert os.path.exists(new_path)
    assert "miku" in new_path


def test_set_collection_move_failure_leaves_state_unchanged(tmp_path, monkeypatch):
    lib = make_lib(tmp_path)
    fn = put_asset(lib, "a.png")
    item = lib.add_item("emoji", "a", [], "local", "", fn, False)
    old_path = lib.asset_path(item)

    def boom(*a, **k):
        raise OSError("locked")
    monkeypatch.setattr(os, "replace", boom)

    lib.set_collection(item["id"], "miku")

    assert lib.get(item["id"])["collection"] == ""  # 변경 안 됨
    assert os.path.exists(old_path)  # 원본 그대로


def test_set_collection_noop_when_same_name(tmp_path):
    lib = make_lib(tmp_path)
    fn = put_asset(lib, "a.png")
    item = lib.add_item("emoji", "a", [], "local", "", fn, False, collection="miku")
    old_path = lib.asset_path(item)
    lib.set_collection(item["id"], "miku")  # 동일 이름
    assert lib.asset_path(lib.get(item["id"])) == old_path
    assert os.path.exists(old_path)
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_library.py -k set_collection -q` → FAIL (현재 `set_collection`은 메타데이터만 바꾸고 파일은 안 옮김)

- [ ] **Step 3: 구현** — `notro_app/library.py`의 `set_collection` 교체

```python
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
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_library.py -q` → 전체 PASS

- [ ] **Step 5: 커밋**

```bash
git add notro_app/library.py tests/test_library.py
git commit -m "feat(library): set_collection physically moves the asset file (move-then-commit)"
```

---

### Task 3: remove_item 경로 버그 수정 + 자동 마이그레이션

**Files:**
- Modify: `notro_app/library.py`
- Test: `tests/test_library.py`

**Interfaces:**
- Produces: `remove_item`이 `asset_path()` 사용. `Library.__init__`이 로드 후 평면 잔존 파일을 자동 이전.

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_library.py`에 추가

```python
def test_remove_item_deletes_asset_in_subfolder(tmp_path):
    lib = make_lib(tmp_path)
    fn = put_asset(lib, "g.gif", collection="miku")
    item = lib.add_item("gif", "g", [], "local", "", fn, True, collection="miku")
    path = lib.asset_path(item)
    assert os.path.exists(path)
    lib.remove_item(item["id"])
    assert not os.path.exists(path)


def test_migration_moves_flat_legacy_files_on_load(tmp_path):
    from notro_app.library import Library
    d = str(tmp_path / "data")
    lib = make_lib_at(d)
    fn = put_asset(lib, "old.png")  # 신규 로직으로는 _uncategorized 아래
    item = lib.add_item("emoji", "old", [], "local", "", fn, False, collection="miku")
    # v2.4 이전 상태를 재현: 파일을 강제로 평면 루트에 둔다
    nested = lib.asset_path(item)
    flat = os.path.join(lib.assets_dir, fn)
    os.replace(nested, flat)
    assert os.path.exists(flat) and not os.path.exists(nested)

    lib2 = Library(d)  # 재로드 -> 마이그레이션 트리거

    assert os.path.exists(nested)
    assert not os.path.exists(flat)
    # 멱등: 다시 로드해도 에러 없이 동일 상태 유지
    lib3 = Library(d)
    assert os.path.exists(nested)
```

`make_lib_at` 헬퍼가 없으면 파일 상단(기존 `make_lib` 근처)에 추가:

```python
def make_lib_at(data_dir):
    from notro_app.library import Library
    return Library(data_dir)
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_library.py -k "remove_item_deletes_asset_in_subfolder or migration_moves" -q` → FAIL

- [ ] **Step 3: 구현** — `notro_app/library.py`

`remove_item` 교체:

```python
    def remove_item(self, item_id: str) -> None:
        item = self._items.pop(item_id, None)
        if item:
            try:
                os.remove(self.asset_path(item))
            except OSError:
                pass
            self._save()
```

`__init__`의 `self._load()` 호출 직후에 추가:

```python
        self._load()
        self._migrate_flat_assets_to_folders()
```

`_load` 메서드 아래(또는 `_apply_folders` 아래)에 신규 메서드:

```python
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
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_library.py -q` → 전체 PASS

- [ ] **Step 5: 커밋**

```bash
git add notro_app/library.py tests/test_library.py
git commit -m "fix(library): remove_item deletes via asset_path; auto-migrate flat legacy files on load"
```

---

### Task 4: fetch.py 신규 등록을 미분류 폴더에 저장

**Files:**
- Modify: `notro_app/fetch.py`

**Interfaces:**
- Consumes: `library.collection_dir("")`
- 기존 `tests/test_fetch.py`는 전부 `lib.asset_path(item)` 경유 검증이라 **수정 불필요** — 회귀만 확인.

- [ ] **Step 1: 구현** — `notro_app/fetch.py`의 `_finalize_asset` 시작 부분에 대상 디렉터리 계산 추가, 이후 `library.assets_dir` 직접 참조 2곳을 `dest_dir`로 교체:

```python
def _finalize_asset(library, tmp_path: str, ext: str) -> tuple[str, bool, bool]:
    """APNG면 GIF로 변환해 저장, 아니면 그대로.

    (최종 파일명, animated, convert_failed) 반환. 신규 등록은 항상 미분류
    폴더에 쓴다 — 사용자가 이후 우클릭으로 컬렉션을 지정하는 기존 흐름과 일치.
    APNG→GIF 변환이 실패하면 정지 PNG(첫 프레임)로 폴백하고 convert_failed=True
    (스펙 §7 — 등록 자체는 성공시키고 항목에 경고 배지를 남긴다)."""
    dest_dir = library.collection_dir("")
    if ext == ".png" and is_apng(tmp_path):
        gif_name = library.new_asset_filename(".gif")
        gif_path = os.path.join(dest_dir, gif_name)
        try:
            apng_to_gif(tmp_path, gif_path)
        except Exception:
            if os.path.exists(gif_path):
                os.remove(gif_path)
            png_name = library.new_asset_filename(".png")
            _first_frame_png(tmp_path, os.path.join(dest_dir, png_name))
            os.remove(tmp_path)
            return png_name, False, True
        os.remove(tmp_path)
        return gif_name, True, False
    filename = library.new_asset_filename(ext)
    final = os.path.join(dest_dir, filename)
    os.replace(tmp_path, final)
    return filename, ext == ".gif" or sniff_animated(final), False
```

(임시 다운로드 파일 `_dl*`/`_cp*`/`_pb*`의 경로는 `register_from_url`/`register_from_file`/`register_from_png_bytes`에서 여전히 `library.assets_dir` 루트를 써도 무방 — 즉시 소비·삭제되는 임시 파일이라 변경 불필요.)

- [ ] **Step 2: 회귀 확인** — Run: `python -m pytest tests/test_fetch.py -q` → 전체 PASS (무변경 통과 — 전부 `lib.asset_path()` 경유 검증)

- [ ] **Step 3: 커밋**

```bash
git add notro_app/fetch.py
git commit -m "feat(fetch): write newly registered assets into the uncategorized subfolder"
```

---

### Task 5: collection_icon (대표 아이콘 후보)

**Files:**
- Modify: `notro_app/library.py`
- Test: `tests/test_library.py`

**Interfaces:**
- Produces: `collection_icon(name: str) -> str | None`.

- [ ] **Step 1: 실패 테스트 작성** — `tests/test_library.py`에 추가

```python
def test_collection_icon_returns_first_registered_item(tmp_path):
    lib = make_lib(tmp_path)
    a = lib.add_item("emoji", "a", [], "local", "",
                     put_asset(lib, "a.png", "miku"), False, collection="miku")
    lib.add_item("emoji", "b", [], "local", "",
                 put_asset(lib, "b.png", "miku"), False, collection="miku")
    assert lib.collection_icon("miku") == a["id"]  # items()는 이름순 -> a가 먼저


def test_collection_icon_covers_folder_scanned_items(tmp_path):
    lib = make_lib(tmp_path)
    folder = tmp_path / "gifs"
    folder.mkdir()
    Image.new("RGB", (4, 4)).save(folder / "x.gif")
    lib.add_folder(str(folder), "gif")
    icon_id = lib.collection_icon("gifs")
    assert icon_id == "folder:" + str(folder / "x.gif")


def test_collection_icon_none_when_empty(tmp_path):
    lib = make_lib(tmp_path)
    assert lib.collection_icon("nope") is None
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_library.py -k collection_icon -q` → FAIL

- [ ] **Step 3: 구현** — `notro_app/library.py`의 `collections()` 메서드 아래에 추가

```python
    def collection_icon(self, name: str) -> str | None:
        """세로 바 대표 아이콘용 첫 항목 id. 등록 항목을 먼저, 그다음 감시
        폴더 스캔 항목 순으로 찾는다(all_display_items() 순서). 없으면 None."""
        for i in self.all_display_items():
            if (i.get("collection") or "") == name:
                return i["id"]
        return None
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_library.py -q` → 전체 PASS

- [ ] **Step 5: 커밋**

```bash
git add notro_app/library.py tests/test_library.py
git commit -m "feat(library): collection_icon() — representative item for the left rail"
```

---

### Task 6: PickerApi가 컬렉션 아이콘 노출

**Files:**
- Modify: `notro_app/picker/window.py`

**Interfaces:**
- Consumes: `library.collections()`, `library.collection_icon()`, `asset_server.url_for()`
- Produces(JS): `get_state().collections`가 `[{name, icon}]` 형태.

- [ ] **Step 1: 구현** — `notro_app/picker/window.py`의 `get_state`에서 `collections` 라인 교체:

```python
    def get_state(self) -> dict:
        from ..i18n import tr
        cols = []
        for name in self._library.collections():
            icon_id = self._library.collection_icon(name)
            cols.append({
                "name": name,
                "icon": self._asset_server.url_for(icon_id) if icon_id else None,
            })
        return {
            "items": [self._display(i) for i in self._library.all_display_items()],
            "recent": [i["id"] for i in self._library.recent()],
            "folders": [{**f, "exists": os.path.isdir(f["path"])}
                        for f in self._library.folders()],
            "collections": cols,
            "strings": {k: tr(k) for k in PICKER_STRING_KEYS},
        }
```

- [ ] **Step 2: 스모크** — Run: `python -c "from notro_app.picker.window import PickerApi; print('ok')"` → `ok`

- [ ] **Step 3: 회귀** — Run: `python -m pytest -q` → 전체 PASS

- [ ] **Step 4: 커밋**

```bash
git add notro_app/picker/window.py
git commit -m "feat(picker-api): expose per-collection representative icon URL"
```

---

### Task 7: UI — 세로 바 아이콘 렌더

**Files:**
- Modify: `notro_app/picker/ui/app.js`, `notro_app/picker/ui/app.css`

**Interfaces:**
- Consumes: `state.collections` = `[{name, icon}]`.

- [ ] **Step 1: app.js — refresh/mock 갱신** — `refresh()`의 `Object.assign` 라인은 그대로(이미 `s.collections`를 옮김, 타입만 객체 배열로 바뀜 — 코드 변경 불필요). `mock()`의 `state.collections = ["miku", "gifs"]` 를 교체:

```js
  state.collections = [
    { name: "miku", icon: sq("#39c5bb") },
    { name: "gifs", icon: null },
  ];
```

- [ ] **Step 2: app.js — renderRail 아이콘 지원** — `renderRail()`을 교체:

```js
function renderRail() {
  const rail = $("#rail");
  rail.innerHTML = "";
  const addBtn = (key, label, title, icon) => {
    const b = document.createElement("button");
    if (icon) {
      const img = document.createElement("img");
      img.src = icon;
      b.appendChild(img);
    } else {
      b.textContent = label;
    }
    b.title = title;
    if (state.collection === key) b.classList.add("active");
    b.addEventListener("click", () => { state.collection = key; renderRail(); render(); });
    rail.appendChild(b);
  };
  addBtn("__fav__", "★", str("picker_col_favorites"), null);
  addBtn("__all__", "▦", str("picker_col_all"), null);
  for (const col of state.collections) {
    addBtn(col.name, col.name.slice(0, 2), col.name, col.icon);
  }
}
```

(`inCollection()`, `filtered()`는 `state.collection`이 여전히 문자열 키라 무변경.)

- [ ] **Step 3: app.css** — `#rail button` 규칙에 `overflow: hidden;` 추가, 그 아래에 신규 규칙:

```css
#rail button { width: 36px; height: 36px; flex: 0 0 36px; border-radius: 50%; border: 0;
        background: var(--panel); color: var(--text); cursor: pointer;
        font-size: 14px; display: flex; align-items: center; justify-content: center;
        overflow: hidden; }
#rail button img {
  width: 100%; height: 100%; object-fit: cover; pointer-events: none;
}
```

(기존 `#rail button` 선언을 위 내용으로 교체 — `overflow: hidden` 한 줄만 추가된 것.)

- [ ] **Step 4: 문법 확인** — Run: `node --check notro_app/picker/ui/app.js` → OK

- [ ] **Step 5: 커밋**

```bash
git add notro_app/picker/ui/app.js notro_app/picker/ui/app.css
git commit -m "feat(picker-ui): render collection representative thumbnail in the left rail"
```

---

### Task 8: 버전 + CHANGELOG

**Files:**
- Modify: `notro_app/__init__.py`, `CHANGELOG.md`

- [ ] **Step 1: 버전** — `notro_app/__init__.py`: `__version__ = "2.4.1"` → `"2.5.0"`.

- [ ] **Step 2: CHANGELOG** — 최상단 `## [2.4.1]` 앞에 삽입:

```markdown
## [2.5.0] - 2026-07-11

### Added
- **Assets are now organized into per-collection folders** on disk
  (`%APPDATA%\Notro\assets\<collection>\`) instead of one flat pile of files —
  opening the library folder (tray, or picker settings) is actually browsable
  now. Existing files migrate automatically the next time Notro starts.
- **Collections show a representative thumbnail** on the left rail instead of
  2-letter text, using the collection's first item (falls back to text if the
  collection is empty).

### Fixed
- `remove_item` now deletes the asset from its actual (collection) folder
  instead of a stale flat path — a latent bug from the v2.4.0 rail feature that
  would have left orphaned files behind.
```

- [ ] **Step 3: 회귀 + 커밋** — Run: `python -m pytest -q` → PASS

```bash
git add notro_app/__init__.py CHANGELOG.md
git commit -m "docs: CHANGELOG [2.5.0], bump to 2.5.0"
```

---

## 최종 통합 검증

- [ ] `python -m pytest -q` → 전체 PASS (79 + 신규)
- [ ] `python -c "from notro_app.app import main; import notro_app; print('v'+notro_app.__version__)"` → `v2.5.0`
- [ ] `node --check notro_app/picker/ui/app.js` → OK
- [ ] 실제 라이브러리(miku 64 + cats 31)로 스모크: `Library(config.DATA_DIR)` 재로드 후 `assets/miku/`, `assets/cats/`, `assets/_uncategorized/` 하위 폴더 생성 확인, 항목 수 불변.
- [ ] 수동 QA(릴리스 전): 실제 피커에서 세로 바에 miku/cats 썸네일 원형 아이콘 표시, 우클릭 컬렉션 이동 시 탐색기에서 파일이 실제로 옮겨지는지, 라이브러리 폴더 열기로 하위 폴더 구조 확인.
