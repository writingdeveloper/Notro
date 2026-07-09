# -*- coding: utf-8 -*-
"""트레이 아이콘·메뉴."""

from __future__ import annotations

import os

import pystray
from PIL import Image, ImageDraw

from . import APP_NAME, __version__, config
from .config import (get_setting_str, is_startup_registered, set_setting_int,
                     set_setting_str, set_startup)
from .i18n import set_language, tr


def make_icon_image(active=True):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    color = (88, 101, 242, 255) if active else (128, 128, 128, 255)  # 디스코드 블루
    d.rounded_rectangle([4, 12, 60, 52], radius=10, fill=color)
    d.ellipse([24, 22, 40, 42], fill=(255, 255, 255, 255))
    return img


def build_icon(monitor, picker=None, listener=None, on_quit_extra=None) -> "pystray.Icon":
    """트레이 아이콘 구성.

    picker/listener가 주어지면 피커 열기·핫키 메뉴가 추가된다 (없으면 v1 메뉴).
    on_quit_extra: 종료 시 추가 정리 콜백.
    """

    def on_toggle(icon, item):
        monitor.enabled = not monitor.enabled
        icon.icon = make_icon_image(monitor.enabled)

    def on_toggle_startup(icon, item):
        try:
            set_startup(not is_startup_registered())
        except Exception:
            icon.notify(tr("notify_startup_fail"), APP_NAME)

    def on_quit(icon, item):
        monitor.stop_flag = True
        if on_quit_extra:
            try:
                on_quit_extra()
            except Exception:
                pass
        icon.stop()

    def on_open_folder(icon, item):
        os.startfile(config.TEMP_DIR)

    def make_open(path):
        def _open(icon, item):
            if os.path.exists(path):
                os.startfile(path)
            else:
                icon.notify(tr("notify_file_deleted"), APP_NAME)
        return _open

    def history_items():
        """최근 처리 내역 서브메뉴 (클릭 시 이미지 열기)."""
        with monitor.history_lock:
            snapshot = list(monitor.history)
        if not snapshot:
            yield pystray.MenuItem(tr("history_empty"), None, enabled=False)
            return
        for e in reversed(snapshot):
            label = f"{e['time']}  {e['orig_mb']:.1f}MB → {e['new_mb']:.1f}MB (-{e['pct']}%)"
            yield pystray.MenuItem(label, make_open(e["path"]))

    def make_limit_item(mb):
        def on_select(icon, item):
            config.set_limit_mb(mb)
            set_setting_int("limit_mb", mb)
            icon.update_menu()

        return pystray.MenuItem(
            f"{mb} MB",
            on_select,
            checked=lambda item, mb=mb: config.LIMIT_MB == mb,
            radio=True,
        )

    # 디스코드 한도: 무료 10 / 니트로 베이직 50 / 니트로 500 MB
    limit_menu = pystray.Menu(
        make_limit_item(10),
        make_limit_item(50),
        make_limit_item(500),
    )

    # 언어 메뉴 (자동 감지 + 각 언어). 언어명은 해당 언어 표기 그대로 둔다.
    lang_names = {
        "en": "English",
        "ko": "한국어",
        "ja": "日本語",
        "zh": "中文(简体)",
        "es": "Español",
    }

    def make_lang_item(code):
        def on_select(icon, item):
            set_setting_str("lang", code)
            set_language(code)
            icon.update_menu()

        label = (lambda item: tr("lang_auto")) if code == "auto" else lang_names[code]
        return pystray.MenuItem(
            label,
            on_select,
            checked=lambda item, code=code: get_setting_str("lang", "auto") == code,
            radio=True,
        )

    lang_menu = pystray.Menu(
        make_lang_item("auto"),
        make_lang_item("en"),
        make_lang_item("ko"),
        make_lang_item("ja"),
        make_lang_item("zh"),
        make_lang_item("es"),
    )

    # ---------- 피커 항목 (picker/listener가 있을 때만) ----------
    picker_items = []
    if picker is not None:
        from .hotkey import HOTKEY_CHOICES, HOTKEY_OFF

        def on_open_picker(icon, item):
            picker.show_at_cursor()

        def make_hotkey_item(key):
            def on_select(icon, item):
                set_setting_str("hotkey", key)
                if listener:
                    listener.set_combo(key)
                icon.update_menu()

            label = (lambda item: tr("hotkey_off")) if key == HOTKEY_OFF \
                else HOTKEY_CHOICES[key][2]
            return pystray.MenuItem(
                label,
                on_select,
                checked=lambda item, key=key: get_setting_str("hotkey", "ctrl+shift+e") == key,
                radio=True,
            )

        hotkey_menu = pystray.Menu(
            *[make_hotkey_item(k) for k in HOTKEY_CHOICES],
            make_hotkey_item(HOTKEY_OFF),
        )
        picker_items = [
            pystray.MenuItem(lambda item: tr("picker_open"), on_open_picker),
            pystray.MenuItem(lambda item: tr("hotkey_menu"), hotkey_menu),
            pystray.Menu.SEPARATOR,
        ]

    icon = pystray.Icon(
        APP_NAME,
        make_icon_image(True),
        tr("tooltip", ver=__version__),
        menu=pystray.Menu(
            *picker_items,
            pystray.MenuItem(
                lambda item: tr("pause") if monitor.enabled else tr("resume"),
                on_toggle,
            ),
            pystray.MenuItem(lambda item: tr("history"), pystray.Menu(history_items)),
            pystray.MenuItem(lambda item: tr("upload_limit"), limit_menu),
            pystray.MenuItem(lambda item: tr("open_folder"), on_open_folder),
            pystray.MenuItem(lambda item: tr("language"), lang_menu),
            pystray.MenuItem(
                lambda item: tr("run_at_startup"),
                on_toggle_startup,
                checked=lambda item: is_startup_registered(),
            ),
            pystray.MenuItem(lambda item: tr("quit"), on_quit),
        ),
    )
    monitor.on_history_change = icon.update_menu
    monitor.status_cb = lambda title, msg: icon.notify(msg, title)
    return icon
