#!/usr/bin/env python3
"""Runner-only real installed EXE first-run Windows GUI smoke.

Starts the ACTUAL installed Notro.exe for a bounded period in a disposable
Windows GitHub Actions desktop, with separate temporary APPDATA. Observes
only windows owned by that one newly started PID via public Win32 APIs:
- first-run welcome visible
- native picker window created (hidden until user invokes it)
- app process remains alive and marks welcome completion
- opt-in auto-send/auto-capture and startup remain disabled

Never interacts with Discord, the user's PC, mouse/keyboard/clipboard,
network services, personal files or installer SmartScreen controls.
This is not human usability approval. No signing is used.
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import subprocess
import tempfile
import time
import winreg
from pathlib import Path

if (os.name != "nt" or os.environ.get("GITHUB_ACTIONS") != "true"
        or not os.environ.get("RUNNER_TEMP")):
    raise SystemExit("Refusing installed EXE GUI QA outside disposable Windows runner.")

user32 = ctypes.windll.user32
user32.EnumWindows.restype = wt.BOOL
user32.EnumWindows.argtypes = [ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM),
                               wt.LPARAM]
user32.GetWindowThreadProcessId.restype = wt.DWORD
user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextLengthW.argtypes = [wt.HWND]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
user32.IsWindowVisible.restype = wt.BOOL
user32.IsWindowVisible.argtypes = [wt.HWND]

SETTINGS = r"Software\Notro"
RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"


def read_setting(name: str, default=None):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, SETTINGS) as key:
            return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return default


def read_startup_registration() -> str | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN) as key:
            return str(winreg.QueryValueEx(key, "Notro")[0])
    except OSError:
        return None


def get_owned_windows(process_id: int) -> list[dict]:
    found = []
    callback_type = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)

    @callback_type
    def visit(hwnd, _):
        current = wt.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(current))
        if current.value != process_id:
            return True
        length = user32.GetWindowTextLengthW(hwnd)
        name = ctypes.create_unicode_buffer(max(length + 1, 1))
        user32.GetWindowTextW(hwnd, name, len(name))
        if name.value:
            found.append({
                "title": name.value[:120],
                "visible": bool(user32.IsWindowVisible(hwnd)),
            })
        return True

    user32.EnumWindows(visit, 0)
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--expected-version", default="2.11.0")
    args = parser.parse_args()
    if not args.exe.is_file() or args.exe.name.lower() != "notro.exe":
        raise SystemExit("Only installed Notro.exe is allowed")
    if "notro" not in str(args.exe).lower():
        raise SystemExit("Unexpected EXE location")

    # Confirm the installed executable version is the intended candidate.
    version_env = os.environ.copy()
    version_env["NOTRO_QA_INSPECT_EXE"] = str(args.exe)
    version_probe = subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command",
         "(Get-Item -LiteralPath $env:NOTRO_QA_INSPECT_EXE)."
         "VersionInfo.ProductVersion.Trim()"],
        capture_output=True, text=True, timeout=15, env=version_env,
    )
    if (version_probe.returncode != 0 or
            version_probe.stdout.strip() != args.expected_version):
        raise SystemExit("Installed candidate ProductVersion mismatch")

    result = {
        "runner_only": True, "exe_started": False,
        "welcome_visible": False, "picker_created": False,
        "auto_send_off": False, "auto_capture_off": False,
        "startup_unchanged": False, "profile_isolated": False,
        "process_alive": False, "errors": [], "passed": False,
    }
    proc = None
    startup_before = read_startup_registration()
    try:
        with tempfile.TemporaryDirectory(
            prefix="notro-installed-first-run-", dir=os.environ["RUNNER_TEMP"]
        ) as folder:
            private_appdata = Path(folder) / "Roaming"
            private_appdata.mkdir()
            env = os.environ.copy()
            env["APPDATA"] = str(private_appdata)
            env["NOTRO_QA_SUPPRESS_AUTORUN"] = "1"
            env.pop("NOTRO_DEBUG_AUTOSHOW", None)
            env.pop("NOTRO_DEBUG", None)

            # The host itself is a single-use GitHub runner. Restrict
            # persistent HKCU settings and avoid update checks or hotkeys.
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, SETTINGS) as key:
                for name, value in (
                    ("welcomed", 0), ("auto_send", 0), ("auto_capture_save", 0),
                    ("auto_update", 0),
                ):
                    winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)
                winreg.SetValueEx(
                    key, "hotkey", 0, winreg.REG_SZ, "off")
                winreg.SetValueEx(
                    key, "lang", 0, winreg.REG_SZ, "en")

            proc = subprocess.Popen(
                [str(args.exe)], cwd=str(args.exe.parent), env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            result["exe_started"] = True
            deadline = time.monotonic() + 35
            while time.monotonic() < deadline:
                if proc.poll() is not None:
                    result["errors"].append(
                        f"installed EXE exited prematurely: {proc.returncode}"
                    )
                    break
                windows = get_owned_windows(proc.pid)
                if any(w["title"] == "Notro" and w["visible"]
                       for w in windows):
                    result["welcome_visible"] = True
                if any(w["title"] == "Notro Picker"
                       for w in windows):
                    result["picker_created"] = True
                if result["welcome_visible"] and result["picker_created"]:
                    time.sleep(0.65)
                    break
                time.sleep(0.3)

            result["process_alive"] = proc.poll() is None
            result["auto_send_off"] = read_setting("auto_send", 1) == 0
            result["auto_capture_off"] = (
                read_setting("auto_capture_save", 1) == 0)
            result["startup_unchanged"] = (
                read_startup_registration() == startup_before)
            result["profile_isolated"] = (
                (private_appdata / "Notro").is_dir()
                and str(private_appdata).startswith(os.environ["RUNNER_TEMP"])
            )
            result["windows"] = get_owned_windows(proc.pid)
            result["welcome_marked"] = read_setting("welcomed", 0) == 1
            result["passed"] = all((
                result["exe_started"], result["welcome_visible"],
                result["picker_created"], result["process_alive"],
                result["auto_send_off"], result["auto_capture_off"],
                result["startup_unchanged"], result["profile_isolated"],
                result["welcome_marked"],
            ))
    except Exception as exc:
        result["errors"].append(type(exc).__name__ + ": " + str(exc)[:300])
    finally:
        if proc is not None:
            try:
                if proc.poll() is None:
                    # Terminate ONLY the tree started by this disposable-runner
                    # test, never any user machine Notro installation.
                    subprocess.run(
                        ["taskkill.exe", "/PID", str(proc.pid), "/T", "/F"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        timeout=10, check=False,
                    )
                proc.wait(timeout=8)
            except (OSError, subprocess.TimeoutExpired):
                if proc.poll() is None:
                    proc.kill()
                    proc.wait(timeout=5)

    print("NOTRO_INSTALLED_EXE_FIRST_RUN_QA="
          + json.dumps(result, ensure_ascii=True), flush=True)
    return 0 if result["passed"] and not result["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
