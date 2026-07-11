# Favorites / Collections / Open-Folder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 피커에 즐겨찾기(favorite), 컬렉션 구분(왼쪽 세로 바), 저장 폴더 열기를 추가하고 기존 미쿠 항목을 `collection="miku"`로 묶는다.

**Architecture:** `library.py` 항목에 `favorite`·`collection` 필드를 더하고 CRUD를 추가한다. `PickerApi`가 이를 노출하고, 피커 UI에 왼쪽 세로 바(★/전체/컬렉션)를 추가해 상단 타입 탭과 교차 필터한다. 트레이·설정에 라이브러리 폴더 열기를 더한다.

**Tech Stack:** Python 표준 라이브러리, 바닐라 JS/HTML/CSS. 신규 의존성 없음.

## Global Constraints

- 항목 신규 필드: `favorite: bool`(기본 False), `collection: str`(기본 ""=전체). `_apply_lib`의 `setdefault`로 하위호환.
- 폴더 스캔 항목은 `collection = os.path.basename(folder path)`(자동). 즐겨찾기·수동 컬렉션은 **등록 항목만**(폴더 항목은 영속 불가).
- 세로 바 48px, 피커 폭 440→500.
- i18n 신규 문자열은 5개 언어 전부.
- 기존 pytest 회귀 없이 통과.
- 미쿠 마이그레이션: `keywords`에 "miku" 포함 등록 항목 → `collection="miku"`.

---

### Task 1: library 즐겨찾기

**Files:**
- Modify: `notro_app/library.py`
- Test: `tests/test_library.py`

**Interfaces:**
- Produces: `add_item(..., favorite=False, collection="")`, `toggle_favorite(id) -> bool`, `favorites() -> list`. `_apply_lib`가 구항목에 `favorite`/`collection` 기본값 백필.

- [ ] **Step 1: 실패 테스트** — `tests/test_library.py`에 추가

```python
def test_toggle_favorite_and_list(tmp_path):
    from notro_app.library import Library
    lib = Library(str(tmp_path))
    it = lib.add_item("emoji", "a", [], "local", "", "a.png", False)
    assert lib.toggle_favorite(it["id"]) is True
    assert [i["id"] for i in lib.favorites()] == [it["id"]]
    assert lib.toggle_favorite(it["id"]) is False
    assert lib.favorites() == []


def test_apply_lib_backfills_new_fields(tmp_path):
    import json
    from notro_app.library import Library
    d = str(tmp_path)
    import os
    os.makedirs(os.path.join(d, "assets"), exist_ok=True)
    with open(os.path.join(d, "library.json"), "w", encoding="utf-8") as f:
        json.dump({"schema": 1, "items": [{"id": "x", "type": "emoji", "name": "n",
                   "keywords": [], "source_kind": "local", "source_url": "",
                   "filename": "n.png", "animated": False, "added_at": 0,
                   "use_count": 0, "last_used": 0}]}, f)
    lib = Library(d)
    it = lib.get("x")
    assert it["favorite"] is False and it["collection"] == ""
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_library.py -k "favorite or backfill" -q` → FAIL

- [ ] **Step 3: 구현** — `notro_app/library.py`

`_apply_lib`의 setdefault 블록:

```python
        for i in data.get("items", []):
            i.setdefault("convert_warning", False)
            i.setdefault("favorite", False)
            i.setdefault("collection", "")
            items[i["id"]] = i
```

`add_item` 시그니처·본문:

```python
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
```

`touch` 아래에 추가:

```python
    def toggle_favorite(self, item_id: str) -> bool:
        item = self._items.get(item_id)
        if not item:
            return False
        item["favorite"] = not item.get("favorite", False)
        self._save()
        return item["favorite"]

    def favorites(self) -> list[dict]:
        return [i for i in self.items() if i.get("favorite")]
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_library.py -k "favorite or backfill" -q` → PASS

- [ ] **Step 5: 커밋**

```bash
git add notro_app/library.py tests/test_library.py
git commit -m "feat(library): per-item favorite flag + backfill"
```

---

### Task 2: library 컬렉션

**Files:**
- Modify: `notro_app/library.py`
- Test: `tests/test_library.py`

**Interfaces:**
- Produces: `set_collection(id, name)`, `collections() -> list[str]`. `scan_folders` 항목에 `collection = basename`.

- [ ] **Step 1: 실패 테스트** — `tests/test_library.py`에 추가

```python
def test_set_collection_and_list(tmp_path):
    from notro_app.library import Library
    lib = Library(str(tmp_path))
    a = lib.add_item("emoji", "a", ["miku"], "local", "", "a.png", False)
    lib.add_item("emoji", "b", [], "local", "", "b.png", False)
    lib.set_collection(a["id"], "miku")
    assert lib.get(a["id"])["collection"] == "miku"
    assert "miku" in lib.collections()


def test_folder_items_collection_is_basename(tmp_path):
    import os
    from notro_app.library import Library
    d = str(tmp_path / "data")
    fol = tmp_path / "gifs"
    fol.mkdir()
    (fol / "x.gif").write_bytes(b"GIF89a")
    lib = Library(d)
    lib.add_folder(str(fol), "gif")
    items = lib.scan_folders()
    assert items and items[0]["collection"] == "gifs"
    assert "gifs" in lib.collections()
```

- [ ] **Step 2: 실패 확인** — Run: `python -m pytest tests/test_library.py -k "collection or basename" -q` → FAIL

- [ ] **Step 3: 구현** — `notro_app/library.py`

`favorites()` 아래:

```python
    def set_collection(self, item_id: str, name: str) -> None:
        item = self._items.get(item_id)
        if item is not None:
            item["collection"] = (name or "").strip()
            self._save()

    def collections(self) -> list[str]:
        regs = {i.get("collection", "") for i in self._items.values()}
        regs.discard("")
        folders = {os.path.basename(f["path"]) for f in self._folders}
        return sorted(regs | folders)
```

`scan_folders`의 항목 dict에 `collection` 추가:

```python
                items.append({
                    "id": "folder:" + ap, "type": dtype, "name": stem,
                    "keywords": [], "source_kind": "folder", "source_url": "",
                    "filename": n, "abs_path": ap,
                    "animated": ext.lower() == ".gif",
                    "collection": os.path.basename(path),
                    "added_at": 0, "use_count": 0, "last_used": 0,
                })
```

- [ ] **Step 4: 통과 확인** — Run: `python -m pytest tests/test_library.py -k "collection or basename" -q` → PASS

- [ ] **Step 5: 커밋**

```bash
git add notro_app/library.py tests/test_library.py
git commit -m "feat(library): per-item collection + folder auto-collection"
```

---

### Task 3: PickerApi 노출 + 폴더 열기

**Files:**
- Modify: `notro_app/picker/window.py`

**Interfaces:**
- Consumes: `library.toggle_favorite/set_collection/collections/favorites`
- Produces(JS): `_display`에 `favorite`/`collection`, `get_state`에 `collections`; `toggle_favorite(id)`, `set_collection(id,name)`, `open_data_dir()`.

- [ ] **Step 1: 구현** — `notro_app/picker/window.py`의 `PickerApi`

`_display` 반환 dict에 두 줄 추가:

```python
            "is_folder": item["source_kind"] == "folder",
            "favorite": bool(item.get("favorite", False)),
            "collection": item.get("collection", ""),
```

`get_state` 반환 dict에 추가:

```python
            "folders": [{**f, "exists": os.path.isdir(f["path"])}
                        for f in self._library.folders()],
            "collections": self._library.collections(),
            "strings": {k: tr(k) for k in PICKER_STRING_KEYS},
```

`remove_item` 아래에 메서드 추가:

```python
    def toggle_favorite(self, item_id: str) -> dict:
        return {"ok": True, "favorite": self._library.toggle_favorite(item_id)}

    def set_collection(self, item_id: str, name: str = "") -> bool:
        self._library.set_collection(item_id, name)
        return True

    def open_data_dir(self) -> bool:
        from .. import config
        try:
            os.startfile(config.DATA_DIR)
        except OSError:
            pass
        return True
```

- [ ] **Step 2: 스모크 + 회귀** — Run: `python -c "from notro_app.picker.window import PickerApi; print('ok')"` → `ok`, 그리고 `python -m pytest -q` → PASS

- [ ] **Step 3: 커밋**

```bash
git add notro_app/picker/window.py
git commit -m "feat(picker-api): expose favorite/collection, toggle_favorite, set_collection, open_data_dir"
```

---

### Task 4: UI 세로 바 + 필터 + Favorites 섹션

**Files:**
- Modify: `notro_app/picker/ui/index.html`, `notro_app/picker/ui/app.css`, `notro_app/picker/ui/app.js`

**Interfaces:**
- Consumes: `get_state().collections`, 항목의 `favorite`/`collection`.

- [ ] **Step 1: index.html** — 본문을 좌측 레일 + 우측 컬럼으로 감싼다. 기존 검색/탭/콘텐츠를 우측에 두고 좌측에 `#rail` 추가. (기존 구조에서 최상위 컨테이너에 `#rail`을 형제로 추가하고 flex로 배치.) 검색바 옆에 설정 버튼은 유지.

```html
<div id="shell">
  <nav id="rail"></nav>
  <div id="main">
    <!-- 기존: 검색바, 탭, #content, 모달들 -->
  </div>
</div>
```

- [ ] **Step 2: app.css** — 폭·레일 스타일 (기존 색 변수 재사용):

```css
body, html { width: 500px; }
#shell { display: flex; height: 100vh; }
#rail { width: 48px; flex: 0 0 48px; background: var(--bg-dark, #1e1f22);
        display: flex; flex-direction: column; align-items: center;
        gap: 6px; padding: 8px 0; overflow-y: auto; }
#rail button { width: 36px; height: 36px; border-radius: 50%; border: 0;
        background: var(--bg, #313338); color: #dbdee1; cursor: pointer;
        font-size: 16px; display: flex; align-items: center; justify-content: center; }
#rail button.active { background: var(--accent, #5865f2); color: #fff; border-radius: 16px; }
#main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.warn-badge, .fav-badge { position: absolute; }
.fav-badge { top: 2px; left: 2px; font-size: 11px; color: #f0b232; }
```

(`.cell`이 `position: relative`인지 확인, 아니면 추가.)

- [ ] **Step 3: app.js — 상태·레일·필터** — `state`에 `collection: "__all__"` 추가. 레일 렌더 + 필터 수정.

```js
const state = { items: [], recent: [], folders: [], collections: [], strings: {},
                tab: "emoji", query: "", collection: "__all__" };

function renderRail() {
  const rail = document.querySelector("#rail");
  rail.innerHTML = "";
  const add = (key, label, title) => {
    const b = document.createElement("button");
    b.textContent = label; b.title = title;
    if (state.collection === key) b.classList.add("active");
    b.addEventListener("click", () => { state.collection = key; renderRail(); render(); });
    rail.appendChild(b);
  };
  add("__fav__", "★", str("picker_col_favorites"));
  add("__all__", "▦", str("picker_col_all"));
  for (const c of state.collections) add(c, c.slice(0, 2), c);
}

function inCollection(i) {
  if (state.collection === "__all__") return true;
  if (state.collection === "__fav__") return i.favorite;
  return (i.collection || "") === state.collection;
}

function filtered() {
  const q = state.query.trim().toLowerCase();
  return state.items.filter((i) => i.type === state.tab && inCollection(i) &&
    (!q || i.name.toLowerCase().includes(q) ||
      i.keywords.some((k) => k.toLowerCase().includes(q))));
}
```

`refresh()`에서 `collections`도 반영: `Object.assign(state, { items: s.items, recent: s.recent, folders: s.folders, collections: s.collections, strings: s.strings });` 그리고 `renderRail()` 호출 추가.

`render()`에 Favorites 섹션 추가 (검색 없고 `__fav__` 뷰 아닐 때, 최근 섹션 위):

```js
  if (!state.query && state.collection !== "__fav__") {
    const favs = items.filter((i) => i.favorite);
    if (favs.length) c.appendChild(section(str("picker_col_favorites"), favs.slice(0, 16)));
  }
```

`section()`의 셀 생성에 favorite 배지:

```js
    if (item.favorite) {
      const fb = document.createElement("span");
      fb.className = "fav-badge"; fb.textContent = "★"; b.appendChild(fb);
    }
```

- [ ] **Step 4: 스모크** — Run: `node --check notro_app/picker/ui/app.js` → OK (문법)

- [ ] **Step 5: 커밋**

```bash
git add notro_app/picker/ui/index.html notro_app/picker/ui/app.css notro_app/picker/ui/app.js
git commit -m "feat(picker-ui): left rail (favorites/all/collections) with cross filter + Favorites section"
```

---

### Task 5: UI 우클릭 — 즐겨찾기 토글 + 컬렉션 이동

**Files:**
- Modify: `notro_app/picker/ui/app.js`

- [ ] **Step 1: 구현** — `showCtx()`에 항목 추가 (등록 항목=`!item.is_folder`일 때):

```js
  add(str("picker_ctx_file"), () => select(item, "file"));
  if (item.can_url) add(str("picker_ctx_url"), () => select(item, "url"));
  if (!item.is_folder) {
    add(item.favorite ? str("picker_ctx_unfavorite") : str("picker_ctx_favorite"),
        async () => { await api().toggle_favorite(item.id); refresh(); });
    add(str("picker_ctx_collection"), async () => {
      const name = window.prompt(str("picker_ctx_collection"), item.collection || "");
      if (name !== null) { await api().set_collection(item.id, name.trim()); refresh(); }
    });
    add(str("picker_ctx_delete"),
        async () => { await api().remove_item(item.id); refresh(); }, true);
  }
```

(주의: `window.prompt`는 WebView2에서 동작한다. 동작 안 하면 §Task5 대안으로 설정 모달 재사용 — 우선 prompt로.)

- [ ] **Step 2: 스모크** — Run: `node --check notro_app/picker/ui/app.js` → OK

- [ ] **Step 3: 커밋**

```bash
git add notro_app/picker/ui/app.js
git commit -m "feat(picker-ui): context menu favorite toggle + move-to-collection"
```

---

### Task 6: 트레이 폴더 열기 + i18n

**Files:**
- Modify: `notro_app/tray.py`, `notro_app/i18n.py`, `notro_app/picker/window.py`(PICKER_STRING_KEYS), `notro_app/picker/ui/app.js`(설정 모달 버튼)

- [ ] **Step 1: i18n** — `notro_app/i18n.py`에 `_UPDATER_STRINGS` 방식(별도 dict + merge)이나 기존 `_PICKER_STRINGS`에 아래 키를 5개 언어 전부 추가. en/ko 예시(ja·zh·es도 채운다):

```python
# en
"picker_ctx_favorite": "Add to favorites",
"picker_ctx_unfavorite": "Remove from favorites",
"picker_ctx_collection": "Move to collection…",
"picker_col_all": "All",
"picker_col_favorites": "Favorites",
"picker_open_library": "Open library folder",
"open_library_folder": "Open library folder",
# ko
"picker_ctx_favorite": "즐겨찾기 추가",
"picker_ctx_unfavorite": "즐겨찾기 제거",
"picker_ctx_collection": "컬렉션 이동…",
"picker_col_all": "전체",
"picker_col_favorites": "즐겨찾기",
"picker_open_library": "라이브러리 폴더 열기",
"open_library_folder": "라이브러리 폴더 열기",
```

- [ ] **Step 2: PICKER_STRING_KEYS** — `notro_app/picker/window.py`의 `PICKER_STRING_KEYS`에 `picker_ctx_favorite`, `picker_ctx_unfavorite`, `picker_ctx_collection`, `picker_col_all`, `picker_col_favorites`, `picker_open_library` 추가.

- [ ] **Step 3: 트레이 메뉴** — `notro_app/tray.py`의 메뉴에서 `open_folder`(출력 폴더) 항목 아래에 라이브러리 폴더 열기 추가:

```python
    def on_open_library(icon, item):
        try:
            os.startfile(config.DATA_DIR)
        except OSError:
            pass
```

메뉴 구성에:

```python
            pystray.MenuItem(lambda item: tr("open_folder"), on_open_folder),
            pystray.MenuItem(lambda item: tr("open_library_folder"), on_open_library),
```

- [ ] **Step 4: 설정 모달 버튼** — `notro_app/picker/ui/app.js`의 설정 모달 로직에 "라이브러리 폴더 열기" 버튼 배선 (index.html에 버튼 있으면 사용; 없으면 `#st-openlib` 추가). 최소: 설정 모달의 폴더 관리 영역에 버튼 추가하고 `api().open_data_dir()` 호출.

- [ ] **Step 5: 회귀 + 커밋** — Run: `python -m pytest -q` → PASS, `python -c "from notro_app.tray import build_icon; print('ok')"`, `node --check notro_app/picker/ui/app.js`

```bash
git add notro_app/tray.py notro_app/i18n.py notro_app/picker/window.py notro_app/picker/ui/app.js
git commit -m "feat: open library folder (tray + settings) + i18n strings"
```

---

### Task 7: 미쿠 컬렉션 마이그레이션

**Files:**
- (일회성 실행 — 사용자 `%APPDATA%\Notro\library.json` 갱신)

- [ ] **Step 1: 실행** — 프로젝트 루트에서 아래를 실행해 `keywords`에 "miku"가 있는 등록 항목을 `collection="miku"`로 설정.

```bash
python - <<'PYEOF'
import os, sys
sys.path.insert(0, os.path.abspath('.'))
from notro_app import config
from notro_app.library import Library
lib = Library(config.DATA_DIR)
n = 0
for it in list(lib._items.values()):
    kws = [k.lower() for k in it.get("keywords", [])]
    if "miku" in kws or "hatsune" in kws:
        lib.set_collection(it["id"], "miku")
        n += 1
print(f"tagged {n} items -> collection 'miku'")
print("collections:", lib.collections())
PYEOF
```

- [ ] **Step 2: 확인** — 출력에 `tagged 64 items` (또는 실제 개수)와 `collections: ['miku']` 확인. (커밋 대상 아님 — 사용자 로컬 데이터.)

---

### Task 8: 버전 + CHANGELOG

**Files:**
- Modify: `notro_app/__init__.py`, `CHANGELOG.md`

- [ ] **Step 1: 버전** — `notro_app/__init__.py`: `__version__ = "2.3.0"` → `"2.4.0"`.

- [ ] **Step 2: CHANGELOG** — 최상단 `## [2.3.0]` 앞에 삽입:

```markdown
## [2.4.0] - 2026-07-10

### Added
- **Favorites** — right-click any item to star it; a Favorites row shows at the
  top and a ★ tab on the left rail filters to just favorites.
- **Collections** — a left rail groups items like Discord's per-server emoji.
  Watched-folder items auto-group by folder name; registered items can be moved
  to a named collection via right-click. The bundled Miku items are grouped as
  **miku**.
- **Open library folder** — from the tray and the picker settings, to browse the
  cached assets (`%APPDATA%\Notro`).
```

- [ ] **Step 3: 회귀 + 커밋** — Run: `python -m pytest -q` → PASS

```bash
git add notro_app/__init__.py CHANGELOG.md
git commit -m "docs: CHANGELOG [2.4.0], bump to 2.4.0"
```

---

## 최종 통합 검증

- [ ] `python -m pytest -q` → 전체 PASS
- [ ] `python -c "from notro_app.app import main; import notro_app; print('v'+notro_app.__version__)"` → `v2.4.0`
- [ ] `node --check notro_app/picker/ui/app.js` → OK
- [ ] 수동 QA(릴리스 전): 세로 바 ★/전체/miku/폴더 필터, 우클릭 즐겨찾기·컬렉션 이동, Favorites 섹션, 트레이·설정 라이브러리 폴더 열기. 실제 피커에서 miku 컬렉션에 64개 표시 확인.
