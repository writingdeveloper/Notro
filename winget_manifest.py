# -*- coding: utf-8 -*-
r"""winget 매니페스트 생성기 (microsoft/winget-pkgs 제출용).

Notro의 EXE에는 코드 서명이 없어 SmartScreen이 경고를 띄운다. 서명서는 유료지만
winget 등록은 무료이고, `winget install writingdeveloper.Notro` 경로가 생기면
"알 수 없는 게시자" 대화상자를 거치지 않아도 된다.

매니페스트에는 **게시된** 릴리스 자산의 URL과 그 파일의 SHA256이 들어간다. 초안
릴리스의 자산 URL은 외부에서 받을 수 없으므로, 릴리스를 publish 한 **뒤에** 실행한다:

    python winget_manifest.py 2.10.0            # -> winget/ 아래 3개 yaml
    python winget_manifest.py 2.10.0 --sha ABC  # 해시를 직접 줄 때

만들어진 파일을 microsoft/winget-pkgs의
`manifests/w/writingdeveloper/Notro/<버전>/` 에 넣어 PR을 올리면 된다
(`winget validate`로 먼저 검증할 것).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import urllib.request

PUBLISHER = "writingdeveloper"
PACKAGE = "Notro"
IDENTIFIER = f"{PUBLISHER}.{PACKAGE}"
REPO = "https://github.com/writingdeveloper/Notro"
MANIFEST_VERSION = "1.6.0"
OUT_DIR = "winget"

# Inno Setup의 제거 레지스트리 키 이름({AppId}_is1). winget이 설치본을 이 패키지와
# 연결하는 열쇠다 — 없으면 ARP 표시 이름으로 추정하는데, Inno 기본 AppVerName이
# "Notro 버전 2.10.0"처럼 언어·버전에 따라 달라져서 매칭이 깨진다(실측 확인).
# AppId는 installer.iss에 고정돼 있으므로 버전이 올라가도 이 값은 변하지 않는다.
PRODUCT_CODE = "{5F8A1E2B-3C4D-4E5F-A6B7-C8D9E0F1A2B3}_is1"


def asset_url(version: str) -> str:
    return f"{REPO}/releases/download/v{version}/NotroSetup.exe"


def fetch_sha256(version: str) -> str:
    """릴리스에 올라간 .sha256 파일을 먼저 쓰고, 없으면 설치 파일을 받아 직접 계산한다."""
    try:
        with urllib.request.urlopen(asset_url(version) + ".sha256", timeout=30) as r:
            return r.read().decode("ascii").split()[0].strip().upper()
    except Exception:
        pass
    with urllib.request.urlopen(asset_url(version), timeout=300) as r:
        h = hashlib.sha256()
        for chunk in iter(lambda: r.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def version_manifest(version: str) -> str:
    return f"""# Created for Notro {version}
PackageIdentifier: {IDENTIFIER}
PackageVersion: {version}
DefaultLocale: en-US
ManifestType: version
ManifestVersion: {MANIFEST_VERSION}
"""


def locale_manifest(version: str) -> str:
    return f"""PackageIdentifier: {IDENTIFIER}
PackageVersion: {version}
PackageLocale: en-US
Publisher: {PUBLISHER}
PublisherUrl: https://github.com/{PUBLISHER}
PublisherSupportUrl: {REPO}/issues
PackageName: {PACKAGE}
PackageUrl: {REPO}
License: MIT
LicenseUrl: {REPO}/blob/main/LICENSE
ShortDescription: Auto-compresses clipboard images for Discord's upload limit and adds an emoji/sticker/GIF picker.
Description: |-
  A tiny Windows tray app for Discord free users. It auto-compresses clipboard images that
  exceed Discord's 10 MB upload limit, compresses oversized video clips with ffmpeg, and
  ships an emoji / sticker / GIF picker opened with a hotkey. It never modifies the Discord
  client and never touches your account or token.
Moniker: notro
Tags:
- clipboard
- compression
- discord
- emoji
- image
- tray
- utility
ReleaseNotesUrl: {REPO}/releases/tag/v{version}
ManifestType: defaultLocale
ManifestVersion: {MANIFEST_VERSION}
"""


def release_date(version: str) -> str:
    """릴리스 게시일 (YYYY-MM-DD). 모르면 빈 문자열 — 선택 필드라 아예 빼면 된다.
    값 없이 `ReleaseDate:`만 남기면 winget validate가 실패한다."""
    api = f"https://api.github.com/repos/{PUBLISHER}/{PACKAGE}/releases/tags/v{version}"
    try:
        req = urllib.request.Request(
            api, headers={"User-Agent": "Notro-winget", "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            import json
            published = json.load(r).get("published_at") or ""
        return published[:10]
    except Exception:
        return ""


def installer_manifest(version: str, sha256: str) -> str:
    # Inno Setup: winget이 /VERYSILENT 등을 자동으로 붙이므로 InstallerSwitches는 비운다.
    # 사용자 범위 설치(%LOCALAPPDATA%)라 Scope는 user.
    date = release_date(version)
    date_line = f"ReleaseDate: {date}\n" if date else ""
    return f"""PackageIdentifier: {IDENTIFIER}
PackageVersion: {version}
MinimumOSVersion: 10.0.0.0
InstallerType: inno
Scope: user
InstallModes:
- interactive
- silent
- silentWithProgress
UpgradeBehavior: install
{date_line}Installers:
- Architecture: x64
  InstallerUrl: {asset_url(version)}
  InstallerSha256: {sha256}
  ProductCode: '{PRODUCT_CODE}'
ManifestType: installer
ManifestVersion: {MANIFEST_VERSION}
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="winget 매니페스트를 만든다")
    ap.add_argument("version", help="릴리스 버전 (예: 2.10.0, v 없이)")
    ap.add_argument("--sha", help="설치 파일 SHA256 (생략하면 릴리스에서 가져온다)")
    args = ap.parse_args()

    version = args.version.lstrip("v")
    sha = (args.sha or "").strip().upper()
    if not sha:
        print(f"릴리스에서 SHA256을 가져오는 중: {asset_url(version)}")
        try:
            sha = fetch_sha256(version)
        except Exception as exc:
            print(f"실패: {exc}\n릴리스를 publish 했는지 확인하거나 --sha로 직접 주세요.",
                  file=sys.stderr)
            return 1

    out = os.path.join(OUT_DIR, version)
    os.makedirs(out, exist_ok=True)
    files = {
        f"{IDENTIFIER}.yaml": version_manifest(version),
        f"{IDENTIFIER}.locale.en-US.yaml": locale_manifest(version),
        f"{IDENTIFIER}.installer.yaml": installer_manifest(version, sha),
    }
    for name, text in files.items():
        path = os.path.join(out, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        print("작성:", path)
    print(f"\nSHA256: {sha}")
    print(f"검증:   winget validate --manifest {out}")
    print(f"제출:   microsoft/winget-pkgs의 manifests/w/{PUBLISHER}/{PACKAGE}/{version}/ 에 PR")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
