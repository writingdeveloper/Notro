# Changelog

All notable changes to this project are documented in this file.
This project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-06-13

### Added
- Initial public release.
- System-tray app that auto-compresses oversized clipboard images for Discord's
  10 MB free upload limit.
- Detection based on the actual PNG bytes Discord would upload, with a safety margin.
- WebP → JPEG quality fallback, then stepwise downscaling, to fit under the limit.
- Compressed image placed on the clipboard **as a file** for direct Ctrl+V upload.
- Opt-in "Run at Windows startup" toggle, recent-history submenu, and single-instance guard.
- Automatic cleanup of temp files older than 1 day.
