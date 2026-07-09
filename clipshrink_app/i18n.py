# -*- coding: utf-8 -*-
"""다국어 (i18n)."""

from __future__ import annotations

import ctypes

kernel32 = ctypes.windll.kernel32

SUPPORTED_LANGS = ("en", "ko", "ja", "zh", "es")

# GetUserDefaultUILanguage()의 primary language id → 언어 코드
_PRIMARY_LANG_MAP = {0x09: "en", 0x12: "ko", 0x11: "ja", 0x04: "zh", 0x0A: "es"}

STRINGS = {
    "en": {
        "tooltip": "ClipShrink v{ver} — auto-compress images for Discord's upload limit",
        "pause": "Pause watching",
        "resume": "Resume watching",
        "history": "Recent activity",
        "history_empty": "(none yet)",
        "upload_limit": "Upload limit",
        "open_folder": "Open output folder",
        "run_at_startup": "Run at Windows startup",
        "language": "Language",
        "lang_auto": "Auto-detect",
        "quit": "Quit",
        "notify_compress_done": "Compressed: {orig:.1f} MB → {new:.1f} MB (-{pct}%, {fmt}) — just paste it.",
        "notify_compress_fail": "Compression failed: couldn't get under the limit.",
        "notify_clipboard_fail": "Clipboard update failed: another app is using the clipboard. Please copy again in a moment.",
        "notify_file_deleted": "That file has already been deleted.",
        "notify_startup_fail": "Failed to change the startup setting.",
        "notify_first_run": "Running in the tray. To launch at startup, enable it from the menu → 'Run at Windows startup'.",
    },
    "ko": {
        "tooltip": "ClipShrink v{ver} — 디스코드 업로드 한도 자동 압축",
        "pause": "감시 중지",
        "resume": "감시 시작",
        "history": "최근 처리 내역",
        "history_empty": "(아직 없음)",
        "upload_limit": "업로드 한도",
        "open_folder": "처리된 이미지 폴더 열기",
        "run_at_startup": "Windows 시작 시 자동 실행",
        "language": "언어",
        "lang_auto": "자동 감지",
        "quit": "종료",
        "notify_compress_done": "압축 완료: {orig:.1f}MB → {new:.1f}MB ({pct}% 감소, {fmt}) — 그대로 붙여넣으세요.",
        "notify_compress_fail": "압축 실패: 한도 이하로 줄이지 못했습니다.",
        "notify_clipboard_fail": "클립보드 교체 실패: 다른 프로그램이 클립보드를 사용 중입니다. 잠시 후 다시 복사해 주세요.",
        "notify_file_deleted": "파일이 이미 삭제되었습니다.",
        "notify_startup_fail": "시작 프로그램 설정 변경에 실패했습니다.",
        "notify_first_run": "트레이에서 실행 중입니다. 부팅 시 자동 실행하려면 메뉴 → 'Windows 시작 시 자동 실행'을 켜세요.",
    },
    "ja": {
        "tooltip": "ClipShrink v{ver} — Discordのアップロード上限に自動圧縮",
        "pause": "監視を停止",
        "resume": "監視を再開",
        "history": "最近の処理履歴",
        "history_empty": "(まだありません)",
        "upload_limit": "アップロード上限",
        "open_folder": "出力フォルダーを開く",
        "run_at_startup": "Windows起動時に実行",
        "language": "言語",
        "lang_auto": "自動検出",
        "quit": "終了",
        "notify_compress_done": "圧縮完了: {orig:.1f}MB → {new:.1f}MB（{pct}%削減、{fmt}）— そのまま貼り付けてください。",
        "notify_compress_fail": "圧縮失敗: 上限以下に縮小できませんでした。",
        "notify_clipboard_fail": "クリップボードの更新に失敗: 他のアプリが使用中です。少し待ってからもう一度コピーしてください。",
        "notify_file_deleted": "ファイルはすでに削除されています。",
        "notify_startup_fail": "スタートアップ設定の変更に失敗しました。",
        "notify_first_run": "トレイで実行中です。起動時に自動実行するには、メニュー →「Windows起動時に実行」をオンにしてください。",
    },
    "zh": {
        "tooltip": "ClipShrink v{ver} — 自动压缩图片以符合 Discord 上传限制",
        "pause": "暂停监视",
        "resume": "恢复监视",
        "history": "最近处理记录",
        "history_empty": "(暂无)",
        "upload_limit": "上传限制",
        "open_folder": "打开输出文件夹",
        "run_at_startup": "开机时自动运行",
        "language": "语言",
        "lang_auto": "自动检测",
        "quit": "退出",
        "notify_compress_done": "压缩完成: {orig:.1f}MB → {new:.1f}MB（减少 {pct}%，{fmt}）— 直接粘贴即可。",
        "notify_compress_fail": "压缩失败: 无法缩小到限制以下。",
        "notify_clipboard_fail": "剪贴板更新失败: 其他程序正在占用剪贴板。请稍后重新复制。",
        "notify_file_deleted": "该文件已被删除。",
        "notify_startup_fail": "更改开机启动设置失败。",
        "notify_first_run": "正在托盘运行。如需开机自动启动，请在菜单 →「开机时自动运行」中开启。",
    },
    "es": {
        "tooltip": "ClipShrink v{ver} — comprime imágenes para el límite de subida de Discord",
        "pause": "Pausar la supervisión",
        "resume": "Reanudar la supervisión",
        "history": "Actividad reciente",
        "history_empty": "(nada todavía)",
        "upload_limit": "Límite de subida",
        "open_folder": "Abrir carpeta de salida",
        "run_at_startup": "Ejecutar al iniciar Windows",
        "language": "Idioma",
        "lang_auto": "Detección automática",
        "quit": "Salir",
        "notify_compress_done": "Comprimido: {orig:.1f} MB → {new:.1f} MB (-{pct}%, {fmt}) — solo pégalo.",
        "notify_compress_fail": "Error de compresión: no se pudo reducir por debajo del límite.",
        "notify_clipboard_fail": "Error al actualizar el portapapeles: otra aplicación lo está usando. Copia de nuevo en un momento.",
        "notify_file_deleted": "Ese archivo ya se ha eliminado.",
        "notify_startup_fail": "No se pudo cambiar la configuración de inicio.",
        "notify_first_run": "Ejecutándose en la bandeja. Para iniciar con el sistema, actívalo en el menú → 'Ejecutar al iniciar Windows'.",
    },
}

current_lang = "en"  # 실행 시 set_language()로 설정됨


def detect_system_lang() -> str:
    """Windows UI 언어를 감지해 지원 언어 코드로 매핑 (실패 시 'en')."""
    try:
        langid = kernel32.GetUserDefaultUILanguage()
        return _PRIMARY_LANG_MAP.get(langid & 0x3FF, "en")
    except Exception:
        return "en"


def set_language(pref: str):
    """pref가 'auto'면 시스템 언어를 감지, 아니면 해당 언어로 설정."""
    global current_lang
    if pref == "auto":
        current_lang = detect_system_lang()
    elif pref in STRINGS:
        current_lang = pref
    else:
        current_lang = "en"


def tr(key: str, **kwargs) -> str:
    """현재 언어의 문자열을 반환 (없으면 영어, 그래도 없으면 key)."""
    table = STRINGS.get(current_lang, STRINGS["en"])
    text = table.get(key) or STRINGS["en"].get(key, key)
    return text.format(**kwargs) if kwargs else text
