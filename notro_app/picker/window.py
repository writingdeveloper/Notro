# -*- coding: utf-8 -*-
"""피커 창 관리 (pywebview). webview 임포트는 지연 — 테스트가 GUI를 안 건드리게."""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
import os
import sys

from .. import clipboard_win as cb
from .. import config
from ..capture_store import (CAPTURE_COLLECTION_ID, CaptureStore,
                             read_clipboard_png)

user32 = ctypes.windll.user32

WIN_W, WIN_H = 500, 420
# 사용자가 늘려 둔 크기를 기억한다. 하한은 세로 바 + 탭이 겹치지 않는 크기,
# 상한은 "커서 옆 팝업"이라는 성격을 잃지 않는 선.
MIN_W, MIN_H = 360, 300
# 상한은 "저장된 값이 터무니없지 않은지"만 본다. 실제로 화면에 넘치는지는 열 때
# 모니터 작업 영역으로 다시 맞추므로(popup_geometry), 여기서 좁게 잡으면 큰 모니터
# 사용자가 늘려 둔 크기가 다음에 열 때 조용히 줄어드는 것처럼 보인다.
MAX_W, MAX_H = 3840, 2160
MONITOR_DEFAULTTONEAREST = 2
GWL_STYLE = -16
WS_THICKFRAME = 0x00040000

# 자동 전송에서 Ctrl+V와 Enter 사이의 간격. 디스코드가 첨부 미리보기를 만들 때까지
# 기다린다 — 너무 짧으면 빈 메시지가 나가고, 너무 길면 자동이라는 느낌이 사라진다.
# 이 값이 맞는지는 기계·파일 크기에 달려 있어서 코드로 정할 수 없다. 레지스트리
# (HKCU\Software\Notro, DWORD auto_send_delay_ms)로 재빌드 없이 조정할 수 있게 둔다.
AUTO_SEND_DELAY = 0.45
AUTO_SEND_DELAY_MIN, AUTO_SEND_DELAY_MAX = 0.05, 5.0


def auto_send_delay() -> float:
    """Ctrl+V와 Enter 사이 대기(초). 설정이 없거나 범위를 벗어나면 기본값."""
    ms = config.get_setting_int("auto_send_delay_ms", int(AUTO_SEND_DELAY * 1000))
    seconds = ms / 1000.0
    if not AUTO_SEND_DELAY_MIN <= seconds <= AUTO_SEND_DELAY_MAX:
        return AUTO_SEND_DELAY
    return seconds

_DEBUG_LOG = os.environ.get("NOTRO_DEBUG", "")


def _dbg(msg: str) -> None:
    if not _DEBUG_LOG:
        return
    try:
        with open(_DEBUG_LOG, "a", encoding="utf-8") as f:
            import time as _t
            f.write(f"{_t.strftime('%H:%M:%S')} {msg}\n")
    except Exception:
        pass


def ui_index_path() -> str:
    """개발 실행과 PyInstaller(--add-data) 실행 모두에서 index.html 절대경로."""
    if getattr(sys, "_MEIPASS", None):
        return os.path.join(sys._MEIPASS, "notro_app", "picker", "ui", "index.html")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "index.html")


class _MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wt.DWORD), ("rcMonitor", wt.RECT),
                ("rcWork", wt.RECT), ("dwFlags", wt.DWORD)]


# 64비트에서 HWND_TOPMOST(-1)가 c_int로 잘려 0xFFFFFFFF(잘못된 핸들)가 되는
# 것을 막기 위해 argtypes를 명시한다 (c_void_p는 -1을 부호 확장한다).
user32.SetWindowPos.restype = wt.BOOL
user32.SetWindowPos.argtypes = [wt.HWND, wt.HWND, ctypes.c_int, ctypes.c_int,
                                ctypes.c_int, ctypes.c_int, wt.UINT]
user32.FindWindowW.restype = wt.HWND
user32.FindWindowW.argtypes = [wt.LPCWSTR, wt.LPCWSTR]
user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
user32.MonitorFromWindow.restype = wt.HANDLE
user32.MonitorFromWindow.argtypes = [wt.HWND, wt.DWORD]
user32.GetWindowLongW.restype = ctypes.c_long
user32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
user32.SetWindowLongW.restype = ctypes.c_long
user32.SetWindowLongW.argtypes = [wt.HWND, ctypes.c_int, ctypes.c_long]
user32.SetForegroundWindow.argtypes = [wt.HWND]
user32.IsWindowVisible.argtypes = [wt.HWND]


def clamp_size(w, h) -> tuple[int, int]:
    """저장된 창 크기를 쓸 수 있는 범위로 자른다 (깨진 값이면 기본 크기)."""
    try:
        w, h = int(w), int(h)
    except (TypeError, ValueError):
        return WIN_W, WIN_H
    if w <= 0 or h <= 0:
        return WIN_W, WIN_H
    return (min(max(w, MIN_W), MAX_W), min(max(h, MIN_H), MAX_H))


def saved_size() -> tuple[int, int]:
    """사용자가 마지막으로 남긴 창 크기 (논리 px). 없으면 기본값."""
    return clamp_size(config.get_setting_int("picker_w", WIN_W),
                      config.get_setting_int("picker_h", WIN_H))


def _monitor_scale(hmon) -> float:
    try:
        shcore = ctypes.windll.shcore
        dx, dy = wt.UINT(), wt.UINT()
        shcore.GetDpiForMonitor(hmon, 0, ctypes.byref(dx), ctypes.byref(dy))
        return dx.value / 96.0 or 1.0
    except Exception:
        return 1.0


def popup_geometry() -> tuple[int, int, int, int]:
    """커서가 있는 모니터의 실제 DPI로 창 크기를 정하고, 커서 위쪽에 오도록
    좌표를 계산해 (x, y, w, h)를 돌려준다 (전부 물리 px — 같은 프로세스에서
    GetCursorPos/GetMonitorInfo/SetWindowPos를 호출해 좌표계를 일치시킨다)."""
    pt = wt.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    hmon = user32.MonitorFromPoint(pt, MONITOR_DEFAULTTONEAREST)
    scale = _monitor_scale(hmon)
    base_w, base_h = saved_size()
    win_w, win_h = int(base_w * scale), int(base_h * scale)
    mi = _MONITORINFO()
    mi.cbSize = ctypes.sizeof(_MONITORINFO)
    user32.GetMonitorInfoW(hmon, ctypes.byref(mi))
    work = mi.rcWork
    # 넓은 모니터에서 늘려 둔 창이 작은 모니터에서 화면 밖으로 나가지 않게 맞춘다.
    # 저장값 자체는 그대로 두므로 원래 모니터로 돌아오면 원래 크기로 열린다.
    win_w = min(win_w, work.right - work.left)
    win_h = min(win_h, work.bottom - work.top)
    x = min(max(pt.x - win_w // 2, work.left), max(work.left, work.right - win_w))
    y = pt.y - win_h - 16
    if y < work.top:
        y = min(pt.y + 16, max(work.top, work.bottom - win_h))
    return x, y, win_w, win_h


def prepare_for_paste(path: str, limit_bytes: int, temp_dir: str,
                      target_px: int = 0) -> tuple[str, bool]:
    """붙여넣기 전처리 (스펙 §6.7/§6.8/§7).

    1) 표시 크기 정규화: target_px > 0이면 긴 변을 그 크기로 맞춘다 (§6.8).
       디스코드는 첨부를 원본 픽셀 크기로 그리므로 이 단계가 곧 "보이는 크기"다.
    2) 한도 초과 처리 —
       정지 이미지: 기존 압축 파이프라인으로 한도 내 재인코딩.
       GIF(애니메이션): 재압축 품질 저하가 커서 그대로 두고 경고만.
    반환: (붙여넣을 경로, 한도 초과 경고 여부)
    """
    from .. import resize

    path = resize.normalize(path, target_px, temp_dir)
    try:
        size = os.path.getsize(path)
    except OSError:
        return path, False
    if size <= limit_bytes:
        return path, False
    if path.lower().endswith(".gif"):
        return path, True
    from datetime import datetime

    from PIL import Image

    from .. import compress

    try:
        with Image.open(path) as img:
            img.load()
            result = compress.compress_image(img, limit_bytes)
    except Exception:
        return path, True
    if result is None:
        return path, True
    data, ext = result
    out = os.path.join(temp_dir,
                       datetime.now().strftime("picker_%Y%m%d_%H%M%S_%f") + ext)
    with open(out, "wb") as f:
        f.write(data)
    return out, False


PICKER_STRING_KEYS = [
    "picker_search", "picker_tab_emoji", "picker_tab_sticker", "picker_tab_gif",
    "picker_recent", "picker_empty", "picker_hint", "picker_add_title",
    "picker_add_url_ph", "picker_add_name_ph", "picker_add_kw_ph",
    "picker_add_collection_ph", "picker_col_uncategorized",
    "picker_add_collection_new", "picker_add_collection_new_ph",
    "picker_add_note", "picker_add_submit", "picker_cancel",
    "picker_folders_title", "picker_add_folder", "picker_drop_hint",
    "picker_ctx_file", "picker_ctx_url", "picker_ctx_delete",
    "picker_err_lottie", "picker_err_not_discord", "picker_err_download",
    "picker_convert_warn", "picker_paste_no_image",
    "picker_ctx_favorite", "picker_ctx_unfavorite", "picker_ctx_collection",
    "picker_col_all", "picker_col_favorites", "picker_open_library",
    "picker_settings",
    "picker_capture_add", "picker_capture_saved", "picker_capture_duplicate",
    "picker_capture_no_image", "picker_capture_read_error",
    "picker_capture_register_error", "picker_capture_collection",
    "picker_auto_capture", "picker_auto_capture_note",
    "picker_settings_title", "picker_folders_subtitle",
    "picker_drop_partial", "picker_drop_failed",
    "picker_paste_size", "picker_paste_size_note", "picker_size_original",
    "picker_auto_send", "picker_auto_send_note",
    "picker_edit_title", "picker_edit_note", "picker_edit_save",
    "picker_ctx_edit", "picker_err_duplicate", "picker_drop_duplicate",
]


def _collection(name) -> str:
    """UI가 넘긴 컬렉션 값 정규화. 세로 바의 가상 항목(전체/즐겨찾기)은
    실제 컬렉션이 아니므로 미분류로 취급한다."""
    name = (name or "").strip()
    return "" if name in ("__all__", "__fav__") else name


class PickerApi:
    """JS 브리지. 각 메서드는 pywebview API 스레드에서 호출된다.

    주의: pywebview는 js_api 객체의 공개 속성을 재귀 탐색해 JS에 노출한다.
    비API 참조(컨트롤러·서버·라이브러리 등)를 공개 속성으로 두면 순환/거대
    그래프 탐색으로 브리지 생성이 멈춘다 — 반드시 `_` 접두 프라이빗으로.
    """

    def __init__(self, library=None, asset_server=None, capture_store=None):
        self._ctrl: PickerController | None = None
        self._library = library
        self._asset_server = asset_server
        self._capture_store = capture_store or (
            CaptureStore(library) if library is not None else None)

    def _display(self, item: dict) -> dict:
        from ..i18n import tr

        collection = item.get("collection", "")
        return {
            "id": item["id"], "type": item["type"], "name": item["name"],
            "keywords": item["keywords"], "animated": item["animated"],
            "url": self._asset_server.url_for(item["id"]),
            "can_url": bool(item.get("source_url")),
            "is_folder": item["source_kind"] == "folder",
            "convert_warning": bool(item.get("convert_warning", False)),
            "favorite": bool(item.get("favorite", False)),
            "collection": collection,
            "collection_label": tr("picker_capture_collection")
            if collection == CAPTURE_COLLECTION_ID else collection,
        }

    def get_state(self) -> dict:
        from .. import resize
        from ..i18n import tr

        cols = []
        for name in self._library.collections():
            icon_id = self._library.collection_icon(name)
            cols.append({
                "name": name,
                "label": tr("picker_capture_collection")
                if name == CAPTURE_COLLECTION_ID else name,
                "icon": self._asset_server.url_for(icon_id) if icon_id else None,
            })
        return {
            "items": [self._display(i) for i in self._library.all_display_items()],
            "recent": [i["id"] for i in self._library.recent()],
            "folders": [{**f, "exists": os.path.isdir(f["path"])}
                        for f in self._library.folders()],
            "collections": cols,
            "auto_capture_save": config.get_setting_flag("auto_capture_save"),
            "auto_send": config.get_setting_flag("auto_send"),
            "capture_collection": CAPTURE_COLLECTION_ID,
            "paste_sizes": resize.current_targets(),
            "paste_size_choices": list(resize.PX_CHOICES),
            "strings": {k: tr(k) for k in PICKER_STRING_KEYS},
        }

    def select_item(self, item_id: str, mode: str = "file") -> bool:
        if self._ctrl:
            self._ctrl.select(item_id, mode)
        return True

    def register_url(self, url: str, name: str = "", keywords: str = "",
                     collection: str = "", type_: str = "") -> dict:
        from .. import fetch
        kws = [k.strip() for k in (keywords or "").replace(",", " ").split()
               if k.strip()]
        try:
            item = fetch.register_from_url(self._library, url, name, kws,
                                           _collection(collection), type_)
        except fetch.UnsupportedAssetError:
            return {"ok": False, "error": "lottie"}
        except fetch.DuplicateAssetError:
            return {"ok": False, "error": "duplicate"}
        except ValueError:
            return {"ok": False, "error": "not_discord"}
        except Exception:
            return {"ok": False, "error": "download"}
        return {"ok": True, "item": self._display(item)}

    def register_files(self, paths, type_: str, collection: str = "") -> dict:
        from .. import fetch
        n = 0
        failed = 0
        duplicate = 0
        target = _collection(collection)
        for p in paths or []:
            try:
                fetch.register_from_file(self._library, p, type_,
                                         collection=target)
                n += 1
            except fetch.DuplicateAssetError:
                duplicate += 1   # 실패가 아니다 — 이미 갖고 있다는 뜻
            except Exception:
                failed += 1
        return {"ok": True, "count": n, "failed": failed, "duplicate": duplicate}

    def update_item(self, item_id: str, name: str = "",
                    keywords: str = "") -> dict:
        """항목 이름·키워드를 고친다 (등록 창과 같은 규칙으로 키워드를 쪼갠다)."""
        kws = [k.strip() for k in (keywords or "").replace(",", " ").split()
               if k.strip()]
        item = self._library.update_item(item_id, name=name, keywords=kws)
        if item is None:
            return {"ok": False, "error": "not_editable"}
        return {"ok": True, "item": self._display(item)}

    def register_capture(self) -> dict:
        """현재 클립보드 이미지를 예약 캡처 컬렉션에 한 번만 저장한다."""
        result = self._capture_store.read_and_save()
        if not result.ok:
            return {"ok": False, "error": result.error or "register"}
        return {
            "ok": True,
            "duplicate": result.duplicate,
            "item_id": result.item_id,
            "collection": CAPTURE_COLLECTION_ID,
        }

    def set_auto_capture_save(self, enabled: bool) -> bool:
        config.set_setting_flag("auto_capture_save", bool(enabled))
        return config.get_setting_flag("auto_capture_save")

    def set_auto_send(self, enabled: bool) -> bool:
        config.set_setting_flag("auto_send", bool(enabled))
        return config.get_setting_flag("auto_send")

    def set_paste_size(self, type_: str, px) -> dict:
        """탭 종류별 붙여넣기 표시 크기를 저장하고 반영된 값을 돌려준다."""
        from .. import resize

        return {"ok": True, "type": type_, "px": resize.set_target_px(type_, px)}

    def register_clipboard(self, type_: str, collection: str = "") -> dict:
        """클립보드의 PNG 이미지를 라이브러리에 등록 (스펙 §5 — 디스코드/브라우저
        에서 이미지를 복사한 뒤 붙여넣는 주 경로). 재인코딩 추정이 아닌 클립보드
        원본 PNG 바이트를 그대로 캐시한다. 이미지가 없으면 ok=False."""
        from datetime import datetime

        from .. import fetch
        read = read_clipboard_png()
        if not read.data:
            return {"ok": False, "error": read.error or "no_image"}
        name = datetime.now().strftime("clip-%Y%m%d-%H%M%S")
        try:
            fetch.register_from_png_bytes(
                self._library, read.data, type_, name=name,
                collection=_collection(collection))
        except fetch.DuplicateAssetError:
            return {"ok": False, "error": "duplicate"}
        except Exception:
            return {"ok": False, "error": "register"}
        return {"ok": True}

    def add_folder(self, default_type: str = "gif") -> dict:
        import webview
        res = self._ctrl.window.create_file_dialog(webview.FOLDER_DIALOG)
        if res:
            self._library.add_folder(res[0], default_type)
            return {"ok": True}
        return {"ok": False}

    def remove_folder(self, path: str) -> bool:
        self._library.remove_folder(path)
        return True

    def remove_item(self, item_id: str) -> bool:
        self._library.remove_item(item_id)
        return True

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

    def hide(self):
        if self._ctrl:
            self._ctrl.hide()
        return True


class PickerController:
    def __init__(self, library=None, api=None):
        self.window = None
        self.prev_hwnd = 0
        self.visible = False
        self.on_notify = None  # tr()된 메시지를 받는 콜백 (트레이 알림)
        self.library = library
        self._api = api

    def _resolve(self, item_id: str) -> dict | None:
        return self.library.resolve(item_id)

    def _notify(self, msg: str) -> None:
        if self.on_notify:
            try:
                self.on_notify(msg)
            except Exception:
                pass

    def select(self, item_id: str, mode: str = "file") -> None:
        """피커 선택 → 숨김 → 클립보드 → 포커스 복귀 → Ctrl+V. 전송은 사용자."""
        import time as _t

        from .. import config, resize
        from ..i18n import tr

        item = self._resolve(item_id)
        if not item:
            return
        self.hide()
        warn = False
        if mode == "url" and item.get("source_url"):
            ok = cb.set_clipboard_text(item["source_url"])
        else:
            path, warn = prepare_for_paste(
                self.library.asset_path(item), config.LIMIT_BYTES,
                config.TEMP_DIR, target_px=resize.target_px_for(item["type"]))
            ok = cb.set_clipboard_file(path)
        focused = cb.focus_window(self.prev_hwnd)
        if ok and focused:
            _t.sleep(0.12)
            cb.send_ctrl_v()
            # 자동 전송(opt-in): 디스코드가 첨부를 입력창에 붙일 시간을 준 뒤
            # Enter를 보낸다. 되돌릴 수 없는 동작이라 기본은 꺼짐이고, 링크로
            # 붙여넣기(mode="url")에는 적용하지 않는다 — 그쪽은 보통 문장 중간에
            # 끼워 넣는 용도라 바로 보내면 곤란하다.
            if mode != "url" and config.get_setting_flag("auto_send"):
                _t.sleep(auto_send_delay())
                cb.send_enter()
            if warn:
                self._notify(tr("picker_oversize_warn"))
        elif ok:
            self._notify(tr("notify_paste_manual"))
        else:
            self._notify(tr("notify_clipboard_fail"))
        self.library.touch(item["id"])

    def create_window(self):
        import webview
        w, h = saved_size()
        self.window = webview.create_window(
            "Notro Picker", url=ui_index_path(), js_api=self._api,
            width=w, height=h, frameless=True, on_top=True,
            hidden=True, resizable=True, easy_drag=False,
            # WS_THICKFRAME을 켜면 OS가 크기 조절을 맡으므로 사용자가 창을 임의로
            # 작게 줄일 수 있다 — 세로 바(48px)와 탭이 겹쳐 레이아웃이 무너진다.
            # pywebview의 min_size는 WinForms MinimumSize로 들어가 테두리 스타일과
            # 무관하게 강제되므로, 저장 시 clamp만 하는 것보다 확실하다.
            min_size=(MIN_W, MIN_H),
        )
        return self.window

    def _remember_size(self) -> None:
        """사용자가 조절한 창 크기를 논리 px로 저장한다 (다음에 그 크기로 열린다).

        물리 px로 저장하면 DPI가 다른 모니터로 옮겼을 때 창이 그만큼 커지거나
        작아지므로, 창이 있는 모니터의 배율로 나눠 논리 크기로 되돌려 둔다.
        """
        hwnd = self._native_hwnd()
        if not hwnd:
            return
        r = wt.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(r)):
            return
        scale = _monitor_scale(
            user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)) or 1.0
        size = clamp_size(round((r.right - r.left) / scale),
                          round((r.bottom - r.top) / scale))
        if size != saved_size():   # 선택할 때마다 hide()가 불리므로 바뀔 때만 쓴다
            config.set_setting_int("picker_w", size[0])
            config.set_setting_int("picker_h", size[1])

    def _native_hwnd(self) -> int:
        return user32.FindWindowW(None, "Notro Picker")

    @staticmethod
    def _enable_resize_border(hwnd: int) -> None:
        """테두리 없는 창에 크기 조절 테두리를 붙인다.

        pywebview는 frameless 창을 FormBorderStyle.None으로 만들고, 이 값이
        resizable 설정을 덮어쓴다(winforms.py). 그 결과 창 가장자리에 히트
        테스트 영역이 없어 마우스로 늘릴 수 없다. WS_THICKFRAME만 다시 켜면
        제목 표시줄 없이 OS가 8방향 크기 조절을 그대로 처리해 준다.
        멱등이므로 표시할 때마다 불러도 된다.
        """
        style = user32.GetWindowLongW(hwnd, GWL_STYLE)
        if style and not style & WS_THICKFRAME:
            user32.SetWindowLongW(hwnd, GWL_STYLE, style | WS_THICKFRAME)

    def show_at_cursor(self):
        import time as _t

        _dbg("show_at_cursor: begin")
        self.prev_hwnd = cb.get_foreground_window()
        try:
            self.window.show()
        except Exception as e:
            _dbg(f"window.show() raised: {e!r}")
            raise
        x, y, w, h = popup_geometry()
        _dbg(f"target geometry: {x},{y} {w}x{h}")
        # pywebview의 show()가 GUI 스레드에서 창을 다시 배치할 수 있으므로,
        # 원하는 지오메트리가 실제 반영될 때까지 검증-재시도한다.
        # SWP_ASYNCWINDOWPOS: 다른 스레드 소유 창에 동기 메시지를 보내지 않아
        # (GUI 스레드가 바쁠 때의) 교착을 원천 차단한다.
        HWND_TOPMOST = -1
        SWP_SHOWWINDOW = 0x0040
        SWP_ASYNCWINDOWPOS = 0x4000
        SWP_FRAMECHANGED = 0x0020
        for i in range(10):
            hwnd = self._native_hwnd()
            if hwnd:
                self._enable_resize_border(hwnd)
                user32.SetWindowPos(hwnd, HWND_TOPMOST, x, y, w, h,
                                    SWP_SHOWWINDOW | SWP_ASYNCWINDOWPOS
                                    | SWP_FRAMECHANGED)
                _t.sleep(0.04)
                r = wt.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(r))
                _dbg(f"attempt {i}: hwnd={hwnd} rect={r.left},{r.top},{r.right},{r.bottom} vis={user32.IsWindowVisible(hwnd)}")
                if abs(r.left - x) <= 2 and abs(r.top - y) <= 2:
                    user32.SetForegroundWindow(hwnd)
                    break
            else:
                _dbg(f"attempt {i}: hwnd not found")
                _t.sleep(0.05)
        self.visible = True
        _dbg("show_at_cursor: end")
        try:
            self.window.evaluate_js("window.__onShow && window.__onShow()")
        except Exception:
            pass

    def hide(self):
        try:
            self._remember_size()
        except Exception:
            pass       # 크기 기억 실패가 창 닫기를 막으면 안 된다
        try:
            self.window.hide()
        except Exception:
            pass
        self.visible = False

    def toggle(self):
        _dbg(f"toggle: visible={self.visible}")
        if self.visible:
            self.hide()
        else:
            self.show_at_cursor()

    def destroy(self):
        try:
            self.window.destroy()
        except Exception:
            pass
