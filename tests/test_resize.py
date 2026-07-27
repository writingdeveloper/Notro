"""붙여넣기 표시 크기 정규화 (스펙 §6.8) — 순수 이미지 처리만, Win32 호출 없음."""

import os

import pytest
from PIL import Image

from notro_app import resize
from notro_app.picker.window import prepare_for_paste


def make_png(path, size=(512, 512), color=(30, 200, 120, 255)):
    Image.new("RGBA", size, color).save(path)
    return str(path)


def make_gif(path, size=(120, 90), frames=6):
    imgs = [Image.new("RGBA", size, (i * 30 % 256, 90, 200, 255)) for i in range(frames)]
    imgs[0].save(path, format="GIF", save_all=True, append_images=imgs[1:],
                 duration=80, loop=0)
    return str(path)


# ---------- 크기 계산 ----------
@pytest.mark.parametrize("w,h,target,expected", [
    (512, 512, 48, (48, 48)),
    (1000, 500, 48, (48, 24)),
    (500, 1000, 48, (24, 48)),
    (20, 20, 48, (48, 48)),        # 작은 원본은 키운다 — 크기 일관성이 목적
    (96, 32, 160, (160, 53)),
    (1, 1000, 48, (1, 48)),        # 얇은 변이 0px로 사라지지 않는다
])
def test_scaled_size_puts_longest_edge_on_target(w, h, target, expected):
    assert resize.scaled_size(w, h, target) == expected


def test_scaled_size_never_returns_zero():
    assert resize.scaled_size(0, 0, 48) == (1, 1)


# ---------- 정지 이미지 ----------
def test_normalize_downscales_still_image(tmp_path):
    src = make_png(tmp_path / "big.png", (512, 400))
    out = resize.normalize(src, 48, str(tmp_path / "cache"))
    assert out != src
    with Image.open(out) as im:
        assert im.size == (48, 38)
    with Image.open(src) as im:
        assert im.size == (512, 400), "원본 파일은 그대로 남아야 한다"


def test_normalize_upscales_tiny_image(tmp_path):
    src = make_png(tmp_path / "tiny.png", (20, 20))
    out = resize.normalize(src, 48, str(tmp_path / "cache"))
    with Image.open(out) as im:
        assert im.size == (48, 48)


def test_normalize_preserves_alpha(tmp_path):
    src = make_png(tmp_path / "clear.png", (256, 256), (255, 0, 0, 0))
    out = resize.normalize(src, 48, str(tmp_path / "cache"))
    with Image.open(out) as im:
        assert im.mode == "RGBA" and im.getpixel((0, 0))[3] == 0


# ---------- 애니메이션 ----------
def total_duration(path):
    """프레임 수는 인코더가 동일한 이웃 프레임을 합치며 줄 수 있으므로(그때
    duration을 앞 프레임에 더한다), 애니메이션이 보존됐는지는 총 재생 시간으로
    본다."""
    from PIL import ImageSequence
    with Image.open(path) as im:
        return sum(int(f.info.get("duration", 0))
                   for f in ImageSequence.Iterator(im))


def test_normalize_keeps_gif_animated(tmp_path):
    src = make_gif(tmp_path / "anim.gif", (120, 90), frames=6)
    out = resize.normalize(src, 48, str(tmp_path / "cache"))
    assert out.endswith(".gif")
    with Image.open(out) as im:
        assert im.size == (48, 36)
        assert getattr(im, "n_frames", 1) > 1, "프레임이 사라지면 정지 이미지가 된다"


def test_normalize_preserves_animation_timing(tmp_path):
    src = make_gif(tmp_path / "anim.gif", (300, 300), frames=8)
    out = resize.normalize(src, 48, str(tmp_path / "cache"))
    assert total_duration(out) == total_duration(src)


def test_normalize_uses_real_format_not_extension(tmp_path):
    """.gif 이름을 달고 있지만 실제로는 정지 PNG인 파일도 깨지지 않는다."""
    src = str(tmp_path / "mislabeled.gif")
    Image.new("RGBA", (200, 200), (10, 20, 30, 255)).save(src, format="PNG")
    out = resize.normalize(src, 48, str(tmp_path / "cache"))
    with Image.open(out) as im:
        assert im.format == "PNG" and im.size == (48, 48)


# ---------- 통과 조건 ----------
def test_normalize_passthrough_when_target_disabled(tmp_path):
    src = make_png(tmp_path / "a.png", (512, 512))
    assert resize.normalize(src, 0, str(tmp_path / "cache")) == src


def test_normalize_passthrough_when_already_target_size(tmp_path):
    src = make_png(tmp_path / "a.png", (48, 30))
    assert resize.normalize(src, 48, str(tmp_path / "cache")) == src


def test_normalize_passthrough_on_unreadable_file(tmp_path):
    bad = tmp_path / "broken.png"
    bad.write_bytes(b"not an image at all")
    out = resize.normalize(str(bad), 48, str(tmp_path / "cache"))
    assert out == str(bad), "정규화 실패가 붙여넣기 자체를 막으면 안 된다"


def test_normalize_passthrough_on_missing_file(tmp_path):
    missing = str(tmp_path / "nope.png")
    assert resize.normalize(missing, 48, str(tmp_path / "cache")) == missing


# ---------- 캐시 ----------
def test_normalize_reuses_cache_without_reencoding(tmp_path):
    """두 번째 붙여넣기는 다시 인코딩하지 않는다 (수 MB GIF에서 수 초 차이)."""
    cache = str(tmp_path / "cache")
    src = make_gif(tmp_path / "anim.gif")
    first = resize.normalize(src, 48, cache)
    with open(first, "rb") as f:
        encoded = f.read()
    sentinel = encoded + b"\x00sentinel"
    with open(first, "wb") as f:      # 재인코딩되면 이 표식이 사라진다
        f.write(sentinel)
    second = resize.normalize(src, 48, cache)
    assert second == first
    with open(second, "rb") as f:
        assert f.read() == sentinel


def test_normalize_cache_key_separates_targets_and_sources(tmp_path):
    cache = str(tmp_path / "cache")
    a = make_png(tmp_path / "a.png", (512, 512), (1, 2, 3, 255))
    b = make_png(tmp_path / "b.png", (512, 512), (4, 5, 6, 255))
    assert resize.normalize(a, 48, cache) != resize.normalize(a, 64, cache)
    assert resize.normalize(a, 48, cache) != resize.normalize(b, 48, cache)


def test_normalize_reencodes_when_source_changes(tmp_path):
    """같은 경로의 파일을 갈아끼우면 옛 캐시를 재사용하지 않는다."""
    cache = str(tmp_path / "cache")
    src = tmp_path / "same-name.png"
    make_png(src, (512, 512))
    first = resize.normalize(str(src), 48, cache)
    make_png(src, (400, 200))
    second = resize.normalize(str(src), 48, cache)
    assert second != first
    with Image.open(second) as im:
        assert im.size == (48, 24)


# ---------- 설정 ----------
def test_defaults_match_discord_display_sizes():
    """48px = 점보 이모지, 160px = 스티커. GIF 탭은 반응짤 자리라 원본 유지."""
    assert resize.TARGETS["emoji"][1] == 48
    assert resize.TARGETS["sticker"][1] == 160
    assert resize.TARGETS["gif"][1] == 0


def test_target_px_for_reads_setting(monkeypatch):
    from notro_app import config
    monkeypatch.setattr(config, "get_setting_int", lambda name, default=0: 96)
    assert resize.target_px_for("emoji") == 96
    assert resize.target_px_for("__unknown__") == 0


def test_set_target_px_clamps_and_saves(monkeypatch):
    from notro_app import config
    saved = {}
    monkeypatch.setattr(config, "set_setting_int",
                        lambda name, value: saved.__setitem__(name, value))
    assert resize.set_target_px("emoji", 9999) == resize.MAX_PX
    assert saved["paste_px_emoji"] == resize.MAX_PX
    assert resize.set_target_px("emoji", -5) == 0
    assert resize.set_target_px("emoji", "nonsense") == 0
    assert resize.set_target_px("__unknown__", 48) == 0


# ---------- 붙여넣기 경로 통합 ----------
def test_prepare_for_paste_normalizes_before_limit_check(tmp_path):
    src = make_png(tmp_path / "huge.png", (1024, 1024))
    path, warn = prepare_for_paste(src, 10_000_000, str(tmp_path), target_px=48)
    assert warn is False and path != src
    with Image.open(path) as im:
        assert im.size == (48, 48)


def test_prepare_for_paste_without_target_is_unchanged(tmp_path):
    src = make_png(tmp_path / "huge.png", (1024, 1024))
    path, warn = prepare_for_paste(src, 10_000_000, str(tmp_path))
    assert path == src and warn is False


def test_prepare_for_paste_oversize_gif_shrinks_under_limit(tmp_path):
    """정규화가 GIF를 한도 아래로 내리면 '너무 큼' 경고 자체가 사라진다."""
    src = make_gif(tmp_path / "big.gif", (600, 600), frames=12)
    limit = os.path.getsize(src) // 4
    path, warn = prepare_for_paste(src, limit, str(tmp_path), target_px=48)
    assert warn is False
    assert os.path.getsize(path) <= limit
