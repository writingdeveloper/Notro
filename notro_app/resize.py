# -*- coding: utf-8 -*-
"""붙여넣기 표시 크기 정규화 (스펙 §6.8).

디스코드는 첨부 이미지를 **원본 픽셀 크기 그대로** 그린다 (임베드 최대치를 넘을
때만 축소). 그래서 라이브러리에 20px짜리와 1000px짜리가 섞여 있으면 붙여넣은
결과도 그만큼 들쭉날쭉해진다 — 실제 커스텀 이모지가 언제나 같은 크기(점보 48px)
로 보이는 것과 정반대다.

붙여넣기 직전에 **긴 변을 목표 크기로 맞춰** 그 느낌을 재현한다. 기본값
(이모지 48px / 스티커 160px)은 같은 문제를 푸는 FakeNitro의 기본값과 같다.

원본 파일은 절대 건드리지 않는다 — 결과는 임시 폴더에 캐시하고, 같은 항목을
다시 붙여넣을 때는 재인코딩 없이 캐시를 쓴다 (수 MB짜리 GIF는 프레임 전체를
다시 인코딩하므로 캐시가 없으면 클릭할 때마다 몇 초씩 걸린다).
"""

from __future__ import annotations

import hashlib
import os
import re

from PIL import Image, ImageSequence

# 목표 크기 선택지 (0 = 원본 유지). FakeNitro의 슬라이더 눈금과 같은 범위에서
# 실제로 쓸 만한 값만 남겼다.
PX_CHOICES = (0, 32, 48, 64, 96, 128, 160)
MAX_PX = 512

# 탭별 (설정 이름, 기본 목표 px).
# 이모지 48 = 디스코드 점보 이모지 크기, 스티커 160 = 디스코드 스티커 표시 크기.
# GIF 탭은 반응짤도 들어가는 자리라 기본은 원본 유지 — 애니메이션 이모지를 GIF
# 탭에 두고 쓰는 사람은 설정에서 켤 수 있다.
TARGETS = {
    "emoji": ("paste_px_emoji", 48),
    "sticker": ("paste_px_sticker", 160),
    "gif": ("paste_px_gif", 0),
}

_CACHE_PREFIX = "np_"
_CACHE_VERSION = 1  # 인코딩 방식이 바뀌면 올려서 옛 캐시를 무효화한다
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


# ---------- 설정 ----------
def target_px_for(type_: str) -> int:
    """탭 종류의 현재 목표 크기 (0이면 정규화하지 않음)."""
    from . import config

    entry = TARGETS.get(type_)
    if entry is None:
        return 0
    name, default = entry
    return _clamp(config.get_setting_int(name, default))


def set_target_px(type_: str, px: int) -> int:
    """탭 종류의 목표 크기를 저장하고 실제 반영된 값을 돌려준다."""
    from . import config

    entry = TARGETS.get(type_)
    if entry is None:
        return 0
    value = _clamp(px)
    config.set_setting_int(entry[0], value)
    return value


def current_targets() -> dict[str, int]:
    return {t: target_px_for(t) for t in TARGETS}


def _clamp(px) -> int:
    try:
        px = int(px)
    except (TypeError, ValueError):
        return 0
    if px <= 0:
        return 0
    return min(px, MAX_PX)


# ---------- 크기 계산 ----------
def scaled_size(w: int, h: int, target_px: int) -> tuple[int, int]:
    """긴 변이 정확히 target_px가 되도록 비율을 유지해 축소/확대한 크기.

    확대도 한다 — 20px 원본만 혼자 먼지처럼 보이면 "크기가 일정하다"는 목적
    자체가 깨지기 때문이다 (뿌옇게 보이는 건 감수한다). FakeNitro도 같은 식
    (scale = 목표 / 긴 변)으로 계산한다.
    """
    longest = max(w, h)
    if longest <= 0:
        return (1, 1)
    scale = target_px / longest
    return (max(1, round(w * scale)), max(1, round(h * scale)))


# ---------- GIF 저장 ----------
def save_gif(frames, durations, dest: str) -> None:
    """RGBA 프레임 목록을 애니메이션 GIF로 저장한다.

    GIF 투명도는 1비트라 알파<128은 완전 투명으로 처리하고, 팔레트 255번을
    투명색으로 예약한다.
    """
    out = []
    for f in frames:
        alpha = f.getchannel("A")
        p = f.convert("RGB").convert("P", palette=Image.ADAPTIVE, colors=255)
        mask = alpha.point(lambda a: 255 if a < 128 else 0)
        p.paste(255, mask)
        out.append(p)
    out[0].save(dest, format="GIF", save_all=True, append_images=out[1:],
                duration=durations, loop=0, disposal=2, transparency=255)


# ---------- 캐시 ----------
def _cache_name(src: str, stat: os.stat_result, target_px: int, ext: str) -> str:
    """(원본 경로·수정시각·크기·목표 px)로 유일해지는 캐시 파일명.

    사람이 임시 폴더를 열어봤을 때 알아볼 수 있도록 원본 이름 앞부분을 남긴다.
    """
    key = f"{os.path.abspath(src)}|{stat.st_mtime_ns}|{stat.st_size}|{target_px}|{_CACHE_VERSION}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    stem = _UNSAFE.sub("_", os.path.splitext(os.path.basename(src))[0])[:24]
    return f"{_CACHE_PREFIX}{stem}_{digest}{ext}"


def normalize(path: str, target_px: int, out_dir: str) -> str:
    """긴 변을 target_px로 맞춘 파일 경로를 돌려준다.

    정규화가 필요 없거나(목표 0, 이미 그 크기) 어떤 이유로든 실패하면 **원본
    경로를 그대로** 돌려준다 — 크기 정규화 때문에 붙여넣기 자체가 실패하는
    일은 없어야 한다.
    """
    if target_px <= 0:
        return path
    try:
        stat = os.stat(path)
    except OSError:
        return path

    dest = ""
    try:
        with Image.open(path) as im:
            w, h = im.size
            if max(w, h) == target_px:
                return path
            animated = bool(getattr(im, "is_animated", False))
            dest = os.path.join(
                out_dir, _cache_name(path, stat, target_px,
                                     ".gif" if animated else ".png"))
            if os.path.exists(dest):
                _touch(dest)          # 자주 쓰는 항목이 임시 정리에 지워지지 않게
                return dest
            os.makedirs(out_dir, exist_ok=True)
            new_size = scaled_size(w, h, target_px)
            if animated:
                _write_animated(im, new_size, dest)
            else:
                _write_still(im, new_size, dest)
    except Exception:
        if dest and os.path.exists(dest):
            try:                      # 부분 생성된 파일을 캐시 히트로 오인하지 않게
                os.remove(dest)
            except OSError:
                pass
        return path
    return dest


def _write_still(im: Image.Image, size: tuple[int, int], dest: str) -> None:
    im.convert("RGBA").resize(size, Image.LANCZOS).save(dest, format="PNG")


def _write_animated(im: Image.Image, size: tuple[int, int], dest: str) -> None:
    frames, durations = [], []
    for frame in ImageSequence.Iterator(im):
        frames.append(frame.convert("RGBA").resize(size, Image.LANCZOS))
        durations.append(int(frame.info.get("duration", 50)) or 50)
    save_gif(frames, durations, dest)


def _touch(path: str) -> None:
    try:
        os.utime(path, None)
    except OSError:
        pass
