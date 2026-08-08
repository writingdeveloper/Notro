# Notro v2.10.3 Release Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare, verify, build, and publish Notro 2.10.3 with consistent version metadata, accurate network disclosures, a valid AVIF dependency floor, and release-time safety gates.

**Architecture:** Keep runtime behavior unchanged and harden the release boundary. A small tested CLI validates tag-to-app version identity, the release workflow runs that validator and the full test suite before packaging, and public documentation/dependency metadata are aligned with the shipped Discord media-link behavior.

**Tech Stack:** Python 3.12, pytest, Pillow 11.3+, GitHub Actions, GitHub CLI, Markdown

## Global Constraints

- Release version is exactly `2.10.3`; release tag is exactly `v2.10.3`.
- Pillow minimum is exactly `11.3.0` because AVIF support is part of the accepted asset contract.
- Network disclosures list both `cdn.discordapp.com` and `media.discordapp.net` without claiming an exact endpoint count.
- General web image URLs remain unsupported.
- Tag/version validation runs only for tag events; manual workflow dispatch remains available.
- The complete pytest suite runs before EXE and installer packaging.
- GitHub Actions creates a draft release; publication happens only after asset and SHA-256 verification.
- Winget manifests are out of scope until the published installer checksum exists.

---

### Task 1: Release identity and AVIF dependency floor

**Files:**
- Modify: `tests/test_i18n.py:94-97`
- Modify: `notro_app/__init__.py:4`
- Modify: `requirements.txt:1`
- Modify: `CHANGELOG.md:6`

**Interfaces:**
- Consumes: existing `notro_app.__version__: str`
- Produces: `notro_app.__version__ == "2.10.3"` and install contract `pillow>=11.3.0`

- [ ] **Step 1: Change the release-version expectation first**

```python
def test_release_version_is_2_10_3():
    """릴리스 문서와 실행 파일 버전이 이전 값으로 남는 회귀를 잡는다."""
    import notro_app
    assert notro_app.__version__ == "2.10.3"
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
python -m pytest tests/test_i18n.py::test_release_version_is_2_10_3 -q
```

Expected: FAIL because the app still reports `2.10.2`.

- [ ] **Step 3: Update version, dependency, and changelog**

Set:

```python
__version__ = "2.10.3"
```

Set the first requirement line to:

```text
pillow>=11.3.0
```

Add this changelog section above 2.10.2:

```markdown
## [2.10.3] - 2026-08-08

### Fixed
- **Discord sticker links copied as media renditions can be registered again.**
  Notro now accepts Discord CDN and media-proxy emoji/sticker variants including
  PNG, GIF, WebP, JPEG, and AVIF, while preserving the working rendition URL.
- **Discord link validation is stricter without rejecting valid mixed-case links.**
  Lookalike Unicode hosts and non-ASCII asset IDs are rejected, and mixed-case
  emoji/sticker paths plus Lottie errors are handled consistently.
```

- [ ] **Step 4: Verify GREEN and generated version metadata**

Run:

```powershell
python -m pytest tests/test_i18n.py::test_release_version_is_2_10_3 tests/test_fetch.py -q
python build_version_file.py
Select-String -Path version_info.txt -Pattern "2.10.3"
```

Expected: focused tests PASS and generated metadata contains `2.10.3`. Do not stage `version_info.txt` because it is generated and ignored.

- [ ] **Step 5: Commit**

```powershell
git add tests/test_i18n.py notro_app/__init__.py requirements.txt CHANGELOG.md
git commit -m "chore: prepare v2.10.3 release metadata"
```

---

### Task 2: Accurate network disclosures

**Files:**
- Modify: `SECURITY.md:33-43`
- Modify: `README.md:154-156`
- Modify: `README.ko.md:147-149`
- Modify: `README.ja.md:150-152`
- Modify: `README.zh.md:138-140`
- Modify: `README.es.md:161-164`

**Interfaces:**
- Consumes: the approved two-host fetch allowlist
- Produces: consistent human-facing disclosure of both Discord asset hosts in all supported documentation languages

- [ ] **Step 1: Update the authoritative security policy**

Replace the exact-count introduction with:

```markdown
Notro contacts only the services documented below:
```

Replace the Discord row with:

```markdown
| `cdn.discordapp.com`, `media.discordapp.net` | Only when you register an emoji or sticker by link | Download that image from Discord |
```

- [ ] **Step 2: Update every translated privacy summary**

Replace the stale network bullet in each README with the corresponding text:

```markdown
# README.md
- It contacts only documented services: GitHub (update checks and the installer,
  SHA-256 verified), `cdn.discordapp.com` and `media.discordapp.net` (only when
  you add an emoji or sticker by link), and PyPI (only the first time you compress
  a video, to get ffmpeg, also SHA-256 verified).

# README.ko.md
- 외부 통신은 문서화된 서비스로만 제한됩니다: GitHub(업데이트 확인과 인스톨러,
  SHA-256 검증), `cdn.discordapp.com`과 `media.discordapp.net`(링크로 이모지나
  스티커를 등록할 때만), PyPI(비디오를 처음 압축할 때 ffmpeg 조달, 역시 SHA-256 검증).

# README.ja.md
- 外部通信は文書化されたサービスに限られます: GitHub（更新確認とインストーラー、
  SHA-256 検証）、`cdn.discordapp.com` と `media.discordapp.net`（リンクで絵文字や
  スタンプを追加するときだけ）、PyPI（初めて動画を圧縮するときの ffmpeg 取得、
  こちらも SHA-256 検証）。

# README.zh.md
- 它只连接有文档说明的服务：GitHub（检查更新与安装包，带 SHA-256 校验）、
  `cdn.discordapp.com` 和 `media.discordapp.net`（仅当你通过链接添加表情或贴纸时）、
  PyPI（仅在你第一次压缩视频、需要获取 ffmpeg 时，同样带 SHA-256 校验）。

# README.es.md
- Solo contacta con servicios documentados: GitHub (comprobación de actualizaciones
  y el instalador, verificado con SHA-256), `cdn.discordapp.com` y
  `media.discordapp.net` (solo cuando añades un emoji o sticker mediante un enlace),
  y PyPI (solo la primera vez que comprimes un vídeo, para obtener ffmpeg, también
  verificado con SHA-256).
```

- [ ] **Step 3: Run disclosure consistency checks**

Run:

```powershell
$docs = 'SECURITY.md','README.md','README.ko.md','README.ja.md','README.zh.md','README.es.md'
foreach ($doc in $docs) {
  $text = Get-Content -Raw $doc
  if ($text -notmatch [regex]::Escape('cdn.discordapp.com') -or
      $text -notmatch [regex]::Escape('media.discordapp.net')) {
    throw "$doc is missing a Discord asset host"
  }
}
rg -n "exactly four|exactly \*\*four|정확히 \*\*네 곳|ちょうど \*\*4 か所|只连接\*\*四|exactamente con \*\*cuatro" SECURITY.md README*.md
```

Expected: every document contains both hosts; the final search returns no stale exact-count claim.

- [ ] **Step 4: Commit**

```powershell
git add SECURITY.md README.md README.ko.md README.ja.md README.zh.md README.es.md
git commit -m "docs: disclose Discord media asset access"
```

---

### Task 3: Testable release tag and workflow gates

**Files:**
- Create: `check_release_version.py`
- Create: `tests/test_release_version_check.py`
- Modify: `.github/workflows/release.yml:20-33`

**Interfaces:**
- Produces: `expected_tag() -> str`, `validate_tag(tag: str) -> None`, and CLI `python check_release_version.py TAG`
- Consumes: `notro_app.__version__ == "2.10.3"`

- [ ] **Step 1: Write failing validator tests**

```python
import subprocess
import sys

import pytest

import check_release_version


def test_expected_tag_uses_app_version():
    assert check_release_version.expected_tag() == "v2.10.3"


def test_validate_tag_accepts_matching_release():
    check_release_version.validate_tag("v2.10.3")


def test_validate_tag_rejects_mismatch():
    with pytest.raises(ValueError, match="expected v2.10.3"):
        check_release_version.validate_tag("v2.10.4")


def test_cli_returns_nonzero_for_mismatched_tag():
    result = subprocess.run(
        [sys.executable, "check_release_version.py", "v2.10.4"],
        text=True, capture_output=True,
    )
    assert result.returncode != 0
    assert "expected v2.10.3" in result.stderr
```

- [ ] **Step 2: Run tests and verify RED**

Run:

```powershell
python -m pytest tests/test_release_version_check.py -q
```

Expected: collection ERROR because `check_release_version.py` does not exist.

- [ ] **Step 3: Implement the minimal validator**

```python
from __future__ import annotations

import argparse

from notro_app import __version__


def expected_tag() -> str:
    return f"v{__version__}"


def validate_tag(tag: str) -> None:
    expected = expected_tag()
    if tag != expected:
        raise ValueError(f"release tag {tag!r} does not match app version; expected {expected}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tag")
    args = parser.parse_args()
    try:
        validate_tag(args.tag)
    except ValueError as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Add workflow gates before packaging**

Change dependency installation to include test requirements:

```yaml
      - name: Install dependencies
        run: pip install --upgrade pyinstaller -r requirements-dev.txt
```

Add immediately afterward:

```yaml
      - name: Verify release tag matches app version
        if: startsWith(github.ref, 'refs/tags/')
        run: python check_release_version.py "${{ github.ref_name }}"

      - name: Run tests
        run: python -m pytest -q
```

- [ ] **Step 5: Verify GREEN and both tag outcomes**

Run:

```powershell
python -m pytest tests/test_release_version_check.py -q
python check_release_version.py v2.10.3
python check_release_version.py v2.10.4
```

Expected: tests PASS; matching command exits 0; mismatched command exits nonzero and prints `expected v2.10.3`.

- [ ] **Step 6: Commit**

```powershell
git add check_release_version.py tests/test_release_version_check.py .github/workflows/release.yml
git commit -m "ci: gate releases on tests and matching version"
```

---

### Task 4: Final local release verification

**Files:**
- Verify only: all files changed by Tasks 1-3

**Interfaces:**
- Consumes: completed 2.10.3 release metadata, disclosures, and workflow gates
- Produces: one verified release commit SHA suitable for pushing and tagging

- [ ] **Step 1: Install exactly the declared dependency floor in an isolated environment**

Create a temporary virtual environment outside the repository, install `requirements-dev.txt` while constraining Pillow to 11.3.0, and run the AVIF regression:

```powershell
$venv = Join-Path $env:TEMP ('notro-v2.10.3-min-' + [guid]::NewGuid())
python -m venv $venv
& "$venv\Scripts\python.exe" -m pip install -r requirements-dev.txt "pillow==11.3.0"
& "$venv\Scripts\python.exe" -m pytest tests/test_fetch.py::test_register_from_url_sniffs_avif_content -q
```

Expected: the AVIF test PASS under Pillow 11.3.0.

- [ ] **Step 2: Run the complete local suite and release checks**

```powershell
python -m pytest -q
python check_release_version.py v2.10.3
git diff --check
git status --short
if (git tag --list v2.10.3) { throw 'Local v2.10.3 tag already exists' }
gh release view v2.10.3 2>$null
if ($LASTEXITCODE -eq 0) { throw 'GitHub v2.10.3 release already exists' }
```

Expected: all tests PASS, tag validator exits 0, no whitespace errors, clean worktree, and neither tag nor release exists. `gh release view` should fail with a not-found result.

---

### Task 5: Deploy and publish v2.10.3

**Files:**
- External state only: GitHub branch, tag, Actions runs, draft release, assets

**Interfaces:**
- Consumes: verified clean `main` SHA from Task 4
- Produces: published GitHub Release `v2.10.3` containing verified `NotroSetup.exe` and `NotroSetup.exe.sha256`

- [ ] **Step 1: Push main and verify branch CI**

```powershell
git push origin main
$verified = git rev-parse HEAD
$ci = gh run list --workflow ci.yml --branch main --limit 1 --json databaseId,headSha,status,conclusion,url | ConvertFrom-Json
if ($ci.headSha -ne $verified) { throw 'Latest main CI run is for the wrong commit' }
gh run watch $ci.databaseId --exit-status
```

Expected: remote `main` points to the intended SHA and CI concludes `success`. Do not tag on failure.

- [ ] **Step 2: Create and push the annotated release tag**

```powershell
$verified = git rev-parse HEAD
git tag -a v2.10.3 $verified -m "Release v2.10.3"
git push origin v2.10.3
```

Expected: tag push succeeds and starts the Release workflow at the verified SHA.

- [ ] **Step 3: Wait for the Release workflow**

```powershell
$verified = git rev-parse 'v2.10.3^{}'
$releaseRun = gh run list --workflow release.yml --branch v2.10.3 --limit 1 --json databaseId,headSha,status,conclusion,url | ConvertFrom-Json
if ($releaseRun.headSha -ne $verified) { throw 'Release workflow is for the wrong commit' }
gh run watch $releaseRun.databaseId --exit-status
```

Expected: workflow concludes `success`. On failure, keep the tag and stop for diagnosis.

- [ ] **Step 4: Verify draft assets and checksum independently**

```powershell
$dir = Join-Path $env:TEMP 'notro-v2.10.3-release'
gh release download v2.10.3 --dir $dir --pattern 'NotroSetup.exe*'
$published = ((Get-Content -Raw "$dir\NotroSetup.exe.sha256") -split '\s+')[0].ToLower()
$actual = (Get-FileHash "$dir\NotroSetup.exe" -Algorithm SHA256).Hash.ToLower()
if ($published -ne $actual) { throw "Release checksum mismatch" }
$draft = gh release view v2.10.3 --json isDraft,tagName,targetCommitish,url,assets,body | ConvertFrom-Json
$draft.body
```

Expected: draft is true, both assets exist, hashes are identical, and the displayed
generated notes accurately cover the 2.10.3 fixes before publication.

- [ ] **Step 5: Review notes, publish, and verify latest release**

```powershell
gh release edit v2.10.3 --draft=false
$published = gh release view v2.10.3 --json isDraft,tagName,url,assets | ConvertFrom-Json
if ($published.isDraft -or $published.tagName -ne 'v2.10.3') { throw 'Release publication state is wrong' }
$latestTag = gh api repos/writingdeveloper/Notro/releases/latest --jq '.tag_name'
if ($latestTag -ne 'v2.10.3') { throw 'v2.10.3 is not the latest published release' }
```

Expected: draft is false, v2.10.3 is latest, and both assets remain present.
