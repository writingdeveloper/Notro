# -*- coding: utf-8 -*-
"""애플리케이션 오케스트레이션."""

from __future__ import annotations

import threading

from . import APP_NAME, config, tray
from .config import (cleanup_temp, ensure_single_instance, get_setting_flag,
                     get_setting_int, get_setting_str, set_setting_flag)
from .i18n import set_language, tr
from .monitor import Monitor


def main():
    ensure_single_instance()
    cleanup_temp()

    # 저장된 업로드 한도 불러오기 (없으면 기본값 유지)
    config.set_limit_mb(get_setting_int("limit_mb", config.LIMIT_MB))

    # 언어: 저장된 설정(없으면 'auto' → 시스템 언어 감지)
    set_language(get_setting_str("lang", "auto"))

    # 자동 시작은 opt-in: 첫 실행이면 안내만 하고, 등록은 사용자가 트레이 메뉴에서 직접 켠다.
    first_run = not get_setting_flag("welcomed")
    if first_run:
        set_setting_flag("welcomed")

    monitor = Monitor()
    threading.Thread(target=monitor.run, daemon=True).start()

    icon = tray.build_icon(monitor)
    if first_run:
        threading.Timer(
            1.5,
            lambda: icon.notify(tr("notify_first_run"), APP_NAME),
        ).start()
    icon.run()
