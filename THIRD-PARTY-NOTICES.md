# Third-party notices

Notro itself is [MIT licensed](LICENSE). The distributed `Notro.exe` bundles the
following third-party components. Their licenses are reproduced by their
respective projects at the links below.

| Component | License | Notes |
|---|---|---|
| [Python](https://www.python.org/) | PSF License | Interpreter and standard library |
| [Pillow](https://python-pillow.org/) | MIT-CMU (HPND) | Image decoding, resizing, encoding |
| [pywebview](https://pywebview.flowrl.com/) | BSD 3-Clause | Picker window (WebView2 host) |
| [pythonnet](https://pythonnet.github.io/) | MIT | Required by pywebview on Windows |
| **[pystray](https://github.com/moses-palmer/pystray)** | **LGPL-3.0** | System tray icon — see below |
| [PyInstaller](https://pyinstaller.org/) | GPL-2.0 **with bootloader exception** | Build tool; the exception permits distributing this application under its own license |

## pystray (LGPL-3.0)

Notro links against pystray, which is licensed under the GNU Lesser General
Public License v3. As required by the LGPL, you may modify or replace pystray in
your installed copy of Notro:

1. Install Notro (default location: `%LOCALAPPDATA%\Programs\Notro`).
2. pystray's modules ship inside `_internal\base_library.zip` (as compiled
   Python). Replace them with your own build of pystray and restart Notro.
3. The rest of Notro's source is available at
   <https://github.com/writingdeveloper/Notro>, so the application can also be
   rebuilt from source against a modified pystray:
   `pip install -r requirements.txt && build.bat`.

pystray's source is available at <https://github.com/moses-palmer/pystray>.

## Not bundled

**ffmpeg is deliberately not distributed with Notro.** Builds that include x264
are GPL-licensed, and shipping them would impose distribution obligations on this
project. Instead, when you first compress a video, Notro downloads the
[imageio-ffmpeg](https://pypi.org/project/imageio-ffmpeg/) wheel from PyPI to your
own machine (verifying its SHA-256) and extracts `ffmpeg.exe` to
`%APPDATA%\Notro\bin`. You can also install ffmpeg yourself and put it on `PATH`;
Notro will use that instead and download nothing.

The **Microsoft Edge WebView2 Runtime** is likewise not bundled. The installer
downloads Microsoft's official bootstrapper only if the runtime is missing.

**Discord** is a trademark of Discord Inc. Notro is an unofficial tool and is not
affiliated with, endorsed by, or sponsored by Discord Inc. No Discord assets are
included in this project.
