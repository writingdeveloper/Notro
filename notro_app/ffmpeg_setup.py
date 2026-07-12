# -*- coding: utf-8 -*-
"""ffmpeg 조달.

ffmpeg를 배포물에 넣지 않는다: (1) 설치 크기를 30MB 늘릴 이유가 없고,
(2) x264가 들어간 빌드는 GPL이라 배포 시 고지 의무가 생긴다. 사용자의 승인 아래
사용자 머신이 PyPI에서 받게 하면 두 문제가 모두 사라진다 — WebView2 부트스트래퍼와 같은 구조.
"""

from __future__ import annotations

import os
import shutil

from . import config


def find_ffmpeg() -> str | None:
    """내려받은 것 → 시스템 PATH 순으로 찾는다. 없으면 None."""
    local = os.path.join(config.BIN_DIR, "ffmpeg.exe")
    if os.path.isfile(local):
        return local
    return shutil.which("ffmpeg")
