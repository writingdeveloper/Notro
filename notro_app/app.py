# -*- coding: utf-8 -*-
"""애플리케이션 오케스트레이션.

스레드 구성:
  - 메인 스레드: webview.start() (WebView2 GUI 루프 — 창 destroy 시 반환)
  - pystray: run_detached() (자체 스레드)
  - HotkeyListener: RegisterHotKey + GetMessage 루프 (전용 스레드)
  - Monitor: 클립보드 감시 (전용 스레드)
WebView2 런타임이 없으면 피커 없이 v1 모드(icon.run이 메인 스레드)로 동작한다.
"""

from __future__ import annotations

import threading

from . import APP_NAME, config, tray
from .config import (cleanup_temp, ensure_single_instance, get_setting_flag,
                     get_setting_int, get_setting_str, set_setting_flag)
from .i18n import set_language, tr
from .monitor import Monitor


def webview2_available() -> bool:
    """WebView2 Evergreen 런타임 설치 여부 (레지스트리)."""
    import winreg
    guid = r"{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
    paths = [
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{guid}"),
        (winreg.HKEY_LOCAL_MACHINE, rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{guid}"),
        (winreg.HKEY_CURRENT_USER, rf"Software\Microsoft\EdgeUpdate\Clients\{guid}"),
    ]
    for root, sub in paths:
        try:
            with winreg.OpenKey(root, sub) as key:
                if winreg.QueryValueEx(key, "pv")[0]:
                    return True
        except OSError:
            continue
    return False


def _enable_dpi_awareness():
    """좌표 계산이 물리 px로 일관되도록 Per-Monitor DPI aware로 설정."""
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _set_app_user_model_id():
    """작업 표시줄이 트레이·피커 창을 Notro exe 아이콘으로 묶어 표시하도록
    명시적 AppUserModelID를 지정한다. 지정하지 않으면 pythonw/WebView2 기본
    아이콘으로 흩어져, 시작 표시줄에 Notro 아이콘 대신 기본 아이콘이 뜬다."""
    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("writingdeveloper.Notro")
    except Exception:
        pass


def main():
    import os
    import sys
    if os.environ.get("NOTRO_DEBUG"):
        import faulthandler
        _fh = open(os.environ["NOTRO_DEBUG"] + ".stacks", "w", encoding="utf-8")
        faulthandler.dump_traceback_later(18, file=_fh)

    _enable_dpi_awareness()
    _set_app_user_model_id()
    ensure_single_instance()
    config.migrate_legacy_data()  # v2.0 ClipShrink → Notro 데이터/설정 이전 (1회)
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

    # 자동 업데이터는 frozen(exe)일 때만. on_ready는 아이콘 생성 후 재배선한다.
    upd = None
    if getattr(sys, "frozen", False):
        from .updater import UpdateChecker
        upd = UpdateChecker(
            os.path.join(config.TEMP_DIR, "update"),
            on_ready=lambda tag, exe: None,
            is_enabled=lambda: config.get_setting_int("auto_update", 1) == 1)

    if not webview2_available():
        # 피커 없이 v1 모드로 동작 (압축 기능은 그대로)
        icon = tray.build_icon(monitor, updater=upd)
        if upd:
            upd.on_ready = lambda tag, exe: tray.signal_update_ready(icon, monitor, tag)
            upd.start()
        if first_run:
            threading.Timer(1.5, lambda: icon.notify(tr("notify_first_run"), APP_NAME)).start()
        threading.Timer(2.5, lambda: icon.notify(tr("notify_webview2_missing"), APP_NAME)).start()
        icon.run()
        return

    import webview

    from .hotkey import HotkeyListener
    from .library import Library
    from .picker.assets_server import AssetServer
    from .picker.window import PickerApi, PickerController

    library = Library(config.DATA_DIR)

    def _resolve_asset(item_id: str):
        item = library.get(item_id)
        if item is None and item_id.startswith("folder:"):
            item = next((i for i in library.scan_folders()
                         if i["id"] == item_id), None)
        return library.asset_path(item) if item else None

    asset_server = AssetServer(_resolve_asset)
    asset_server.start()

    api = PickerApi(library=library, asset_server=asset_server)
    picker = PickerController(library=library, api=api)
    api._ctrl = picker
    listener = HotkeyListener(on_hotkey=picker.toggle)

    from . import video as _video

    icon = tray.build_icon(
        monitor, picker=picker, listener=listener, updater=upd,
        on_quit_extra=lambda: (listener.stop(), asset_server.stop(), picker.destroy(),
                               _video.terminate_all(),   # 인코딩 중이면 ffmpeg를 죽인다
                               upd.stop() if upd else None),
    )
    listener.on_register_fail = lambda label: icon.notify(
        tr("notify_hotkey_fail", combo=label), APP_NAME)
    picker.on_notify = lambda msg: icon.notify(msg, APP_NAME)
    if upd:
        upd.on_ready = lambda tag, exe: tray.signal_update_ready(icon, monitor, tag)
        upd.start()

    def _handle_video(path: str):
        """한도 초과 비디오: 확인 창 → (필요시 ffmpeg 다운로드) → 인코딩 → 클립보드 교체.
        monitor 스레드를 막지 않도록 별도 스레드에서 돈다. 클립보드는 성공했을 때만 바꾼다."""
        import os as _os

        from . import ffmpeg_setup, video
        from . import clipboard_win as _cb
        from .video_window import VideoWindow, fmt_dur, fmt_size

        ff = ffmpeg_setup.find_ffmpeg()
        name = _os.path.basename(path)
        try:
            src_size = _os.path.getsize(path)
        except OSError:
            return

        meta = video.probe(ff, path) if ff else None
        if ff and meta is None:
            # ffmpeg는 있는데 읽지 못했다 = 비디오가 아니거나 손상됐다.
            # 창도 띄우지 않고 조용히 무시한다 (spec §5) — 오탐으로 사용자를 방해하지 않는다.
            return
        plan = video.plan_encode(meta, config.LIMIT_BYTES) if meta else None

        if meta and not plan:                       # 하한 미달 — 정직하게 실패
            limit = fmt_size(config.LIMIT_BYTES)
            w = VideoWindow(tr("video_confirm_title"),
                            tr("video_meta", name=name, size=fmt_size(src_size),
                               dur=fmt_dur(meta.duration), res=f"{meta.height}p"),
                            tr("video_fail_toobig", limit=limit), None,
                            tr("video_btn_close"))
            w.show()
            return

        if ff and meta and plan:
            est = tr("video_estimate", size=fmt_size(config.LIMIT_BYTES),
                     res=f"{plan.height}p{plan.fps}")
            meta_line = tr("video_meta", name=name, size=fmt_size(src_size),
                           dur=fmt_dur(meta.duration), res=f"{meta.height}p{int(meta.fps)}")
            warn = tr("video_warn_quality") if plan.warn else None
            accept = tr("video_btn_compress")
        else:                                       # ffmpeg가 없다 — 먼저 받아야 한다
            est = tr("video_need_ffmpeg", mb=ffmpeg_setup.DOWNLOAD_MB)
            meta_line = tr("video_meta", name=name, size=fmt_size(src_size), dur="-", res="-")
            warn = None
            accept = tr("video_btn_compress")

        w = VideoWindow(tr("video_confirm_title"), meta_line, est, warn, accept)
        w.show()

        def _work():
            if not w.accepted.wait(timeout=300):    # 5분 내 응답 없으면 포기
                return
            nonlocal ff, meta, plan
            if not ff:
                ff = ffmpeg_setup.download_ffmpeg(
                    on_progress=lambda frac: w.set_progress(
                        tr("video_downloading", pct=int(frac * 100)), int(frac * 100)))
                if not ff:
                    w.finish(tr("video_fail_download"))
                    return
                meta = video.probe(ff, path)
                plan = video.plan_encode(meta, config.LIMIT_BYTES) if meta else None
                if not plan:
                    w.finish(tr("video_fail_toobig", limit=fmt_size(config.LIMIT_BYTES)))
                    return

            out = _os.path.join(config.TEMP_DIR,
                                _os.path.splitext(name)[0] + "_notro.mp4")
            for attempt in range(2):                # 1-pass 오차 → 1회만 재시도
                ok = video.encode(
                    ff, path, plan, out,
                    on_progress=lambda done: w.set_progress(
                        tr("video_encoding", pct=int(done / meta.duration * 100)),
                        int(done / meta.duration * 100)),
                    should_cancel=w.cancelled.is_set)
                if w.cancelled.is_set():
                    if _os.path.exists(out):
                        _os.remove(out)
                    return
                if not ok:
                    w.finish(tr("video_fail_encode"))
                    return
                if _os.path.getsize(out) <= config.LIMIT_BYTES:
                    break
                if attempt == 0:                    # 여전히 크다 — 비트레이트를 낮춰 한 번 더
                    plan = video.EncodePlan(plan.height, plan.fps,
                                            int(plan.video_kbps * 0.8),
                                            plan.audio_kbps, plan.warn)
                else:
                    w.finish(tr("video_fail_encode"))
                    return

            if _cb.set_clipboard_file(out):
                monitor.last_seq = _cb.get_sequence_number()   # 자기 출력 재처리 방지
                w.finish(tr("video_done", size=fmt_size(_os.path.getsize(out))))
            else:
                w.finish(tr("notify_clipboard_fail"))

        threading.Thread(target=_work, daemon=True).start()

    def _on_video_oversize(path: str):
        # monitor.py는 이 콜백을 감싸지 않고 직접 호출한다 — 다른 선택적 콜백인
        # status_cb/on_history_change는 try/except로 감싸져 있는 것과 다르다(리뷰 지적).
        # 여기서 예외를 삼켜야 클립보드 감시 루프가 죽지 않는다.
        try:
            threading.Thread(target=_handle_video, args=(path,), daemon=True).start()
        except Exception:
            pass

    monitor.on_video_oversize = _on_video_oversize

    picker.create_window()
    icon.run_detached()
    combo = get_setting_str("hotkey", "ctrl+shift+e")
    if combo != "off":
        listener.start(combo)
    if first_run:
        # 창이 없는 트레이 앱이라 첫 실행에는 앱이 떴는지조차 모르기 쉽다 — 특히
        # Windows 11은 새 트레이 아이콘을 기본으로 숨긴다. 그래서 사용자가 직접 읽고
        # 닫는 안내 창을 띄운다. (토스트는 알림을 끈 사용자에게 아예 도달하지 못하고,
        # 시간 기반 자동 팝업은 설치 마법사의 완료 화면을 덮어버린다.) 안내 창에는
        # 트레이에 뜨는 것과 같은 아이콘을 심어 무엇을 찾아야 하는지 보여준다.
        from . import welcome
        from .hotkey import label_for
        combo_label = label_for(combo) if combo != "off" else None
        welcome.create_window(combo_label)
        first_msg = (tr("notify_first_run_picker", combo=combo_label)
                     if combo_label else tr("notify_first_run"))
        threading.Timer(1.5, lambda: icon.notify(first_msg, APP_NAME)).start()

    # QA 훅: 핫키와 동일한 코드 경로(toggle)를 합성 키 입력 없이 구동
    import os
    if os.environ.get("NOTRO_DEBUG_AUTOSHOW"):
        threading.Timer(3.0, picker.toggle).start()

    # http_server=False: UI를 file:// origin으로 로드해 로컬 자산 <img src="file:///...">
    # 로드가 차단되지 않게 한다 (내부 HTTP 서버 origin에서는 local resource 차단됨)
    webview.start(gui="edgechromium", http_server=False)  # 메인 스레드 블록
    monitor.stop_flag = True
