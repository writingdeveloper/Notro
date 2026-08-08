# Discord Asset Link Variants Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Accept every approved Discord emoji and sticker CDN/media link variant while continuing to reject non-Discord URLs and unsupported Lottie source files.

**Architecture:** Extend the fetch parser so a `ParsedAsset` retains the exact validated Discord URL in addition to its kind, ID, and extension. The downloader will continue probing the canonical GIF variant for animation, then fall back to the validated input rendition instead of constructing a potentially nonexistent CDN URL.

**Tech Stack:** Python 3, standard-library regular expressions and URL handling, Pillow, pytest

## Global Constraints

- Only `cdn.discordapp.com` and `media.discordapp.net` are allowed.
- Only `/emojis/{numeric-id}.{extension}` and `/stickers/{numeric-id}.{extension}` are allowed.
- Accepted image extensions are PNG, GIF, WebP, JPG/JPEG, and AVIF, case-insensitively.
- Existing `<:name:id>` and `<a:name:id>` inputs remain supported.
- Direct sticker `.json` inputs retain the Lottie-specific error.
- General web image URLs remain rejected.

---

### Task 1: Parse and retain validated Discord asset URLs

**Files:**
- Modify: `tests/test_fetch.py:60-100`
- Modify: `notro_app/fetch.py:21-113`

**Interfaces:**
- Consumes: `parse_discord_url(text: str) -> ParsedAsset | None`
- Produces: `ParsedAsset.source_url: str`, containing the exact validated URL for URL inputs and an empty string for custom-emoji tags

- [ ] **Step 1: Write failing parser tests**

Add table-driven tests with literal expectations:

```python
@pytest.mark.parametrize("url,kind,ext", [
    ("https://media.discordapp.net/stickers/123.webp?size=160&quality=lossless", "sticker", "webp"),
    ("https://media.discordapp.net/stickers/123.jpg?size=160", "sticker", "jpg"),
    ("https://media.discordapp.net/stickers/123.JPEG?size=160", "sticker", "jpeg"),
    ("https://media.discordapp.net/stickers/123.avif?size=160", "sticker", "avif"),
    ("https://cdn.discordapp.com/stickers/123.gif", "sticker", "gif"),
    ("https://media.discordapp.net/emojis/456.webp?size=96", "emoji", "webp"),
    ("https://media.discordapp.net/emojis/456.avif?size=96", "emoji", "avif"),
])
def test_parse_discord_asset_variants_preserves_validated_url(url, kind, ext):
    parsed = fetch.parse_discord_url(url)
    assert parsed is not None
    assert (parsed.kind, parsed.asset_id, parsed.ext) == (kind, url.split("/")[-1].split(".")[0], ext)
    assert parsed.source_url == url


@pytest.mark.parametrize("url", [
    "https://cdn.discordapp.com.evil.example/stickers/123.webp",
    "https://media.discordapp.net/attachments/123/456.webp",
    "https://media.discordapp.net/stickers/not-an-id.webp",
    "https://media.discordapp.net/stickers/123.svg",
    "https://media.discordapp.net/stickers/123.webp.evil",
    "https://example.com/stickers/123.webp",
])
def test_parse_discord_asset_variants_rejects_unapproved_urls(url):
    assert fetch.parse_discord_url(url) is None
```

Also extend the existing emoji-tag test with:

```python
assert p.source_url == ""
```

- [ ] **Step 2: Run parser tests and verify RED**

Run:

```powershell
pytest tests/test_fetch.py -k "asset_variants or emoji_tag or lottie" -v
```

Expected: FAIL because WebP/JPEG/AVIF sticker links are not parsed and `ParsedAsset` has no `source_url`.

- [ ] **Step 3: Implement the minimal validated parser**

In `notro_app/fetch.py`, replace the separate loose URL patterns with a full Discord asset URL matcher covering the approved hosts, paths, extensions, and optional query. Add `source_url: str = ""` to `ParsedAsset`. For a URL match, normalize only `kind` and `ext`, and store `m.group(0)` as `source_url`. Preserve the existing Lottie exception for sticker `.json`, reject emoji `.json`, and leave emoji-tag parsing unchanged apart from the new default field.

Use a boundary-aware pattern so a lookalike suffix cannot satisfy the host check:

```python
DISCORD_ASSET_RE = re.compile(
    r"https://(?:cdn\.discordapp\.com|media\.discordapp\.net)/"
    r"(?P<kind>emojis|stickers)/(?P<id>\d+)\."
    r"(?P<ext>png|gif|webp|jpe?g|avif|json)"
    r"(?:\?[^\s<>\"']*)?(?=$|[\s<>\"'])",
    re.I,
)
```

- [ ] **Step 4: Run parser tests and verify GREEN**

Run:

```powershell
pytest tests/test_fetch.py -k "parse or emoji_tag" -v
```

Expected: all selected tests PASS.

- [ ] **Step 5: Commit the parser change**

```powershell
git add tests/test_fetch.py notro_app/fetch.py
git commit -m "fix(fetch): accept Discord asset link variants"
```

---

### Task 2: Download the validated media rendition

**Files:**
- Modify: `tests/test_fetch.py:115-150`
- Modify: `notro_app/fetch.py:31-33,228-253`

**Interfaces:**
- Consumes: `ParsedAsset.source_url: str` from Task 1
- Produces: `_download_asset(library, p) -> tuple[str, str, str]`, whose third element is the URL that actually supplied the saved asset

- [ ] **Step 1: Write a failing registration test**

Add a test whose observable saved metadata proves that the media rendition, not a reconstructed CDN WebP URL, was used:

```python
def test_register_from_media_sticker_preserves_working_rendition(tmp_path, monkeypatch):
    lib = Library(str(tmp_path / "d"))
    media_url = (
        "https://media.discordapp.net/stickers/961508283863138324.webp"
        "?size=160&quality=lossless"
    )

    monkeypatch.setattr(fetch, "download", fake_download(static_webp_bytes()))
    item = fetch.register_from_url(lib, media_url)

    assert item["type"] == "sticker"
    assert item["source_url"] == media_url
    assert item["filename"].endswith(".webp")
    assert os.path.exists(lib.asset_path(item))
```

This test mocks only external network I/O; parsing, download selection, content sniffing, storage, and metadata creation remain real.

- [ ] **Step 2: Run the registration test and verify RED**

Run:

```powershell
pytest tests/test_fetch.py::test_register_from_media_sticker_preserves_working_rendition -v
```

Expected: FAIL because `_download_asset` stores a reconstructed `cdn.discordapp.com/...webp` URL rather than the validated media URL.

- [ ] **Step 3: Implement validated-source fallback**

In `_download_asset`, retain the existing animated-GIF probe. When it does not yield a multiframe GIF, set the fallback URL to `p.source_url or canonical_url(p)` and download that URL. Keep returning the URL that actually succeeded. Add `"AVIF": ".avif"` to `FORMAT_EXTS` so supported Pillow builds preserve the detected format rather than trusting a misleading URL suffix.

The fallback must be exactly:

```python
ext = "." + p.ext
url = p.source_url or canonical_url(p)
tmp = os.path.join(library.assets_dir, "_dl" + library.new_asset_filename(ext))
download(url, tmp)
return tmp, ext, url
```

- [ ] **Step 4: Run focused fetch tests and verify GREEN**

Run:

```powershell
pytest tests/test_fetch.py -v
```

Expected: all fetch tests PASS with no warnings.

- [ ] **Step 5: Run the complete suite**

Run:

```powershell
pytest -q
```

Expected: the complete suite PASS with no failures.

- [ ] **Step 6: Commit the downloader change**

```powershell
git add tests/test_fetch.py notro_app/fetch.py
git commit -m "fix(fetch): preserve Discord media rendition URLs"
```

---

### Task 3: Final regression verification

**Files:**
- Verify only: `notro_app/fetch.py`, `tests/test_fetch.py`

**Interfaces:**
- Consumes: completed parser and downloader behavior from Tasks 1-2
- Produces: verified release-ready behavior; no new interface

- [ ] **Step 1: Run static repository checks**

Run:

```powershell
git diff --check HEAD~2..HEAD
git status --short
```

Expected: no whitespace errors; only intentional changes are present.

- [ ] **Step 2: Run the complete suite once more from a clean process**

Run:

```powershell
pytest -q
```

Expected: all tests PASS with no failures.

- [ ] **Step 3: Inspect the final diff against the approved design**

Confirm each approved behavior is represented by an executable test: allowed hosts and paths, supported extensions, query preservation, emoji tags, Lottie error, and rejection cases. Do not add unrelated refactors.
