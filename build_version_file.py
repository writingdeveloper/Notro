# -*- coding: utf-8 -*-
"""PyInstaller용 VSVersionInfo 파일 생성 (exe 속성창의 버전·제작자 정보).

exe에 버전 리소스가 없으면 파일 속성 대화상자가 텅 비고, SmartScreen의 평판 판단에도
불리하다. 버전은 notro_app.__version__ 하나만 보고 만들어 이중 관리를 피한다.

    python build_version_file.py                      # -> version_info.txt
    pyinstaller ... --version-file version_info.txt   # 빌드에서 사용
"""

from notro_app import __version__

_parts = (__version__.split(".") + ["0", "0", "0", "0"])[:4]
_nums = ", ".join(str(int(p)) for p in _parts)

VERSION_INFO = f"""VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({_nums}),
    prodvers=({_nums}),
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', 'writingdeveloper'),
        StringStruct('FileDescription', 'Notro - Discord clipboard compressor and emoji picker'),
        StringStruct('FileVersion', '{__version__}'),
        StringStruct('InternalName', 'Notro'),
        StringStruct('LegalCopyright', 'MIT License'),
        StringStruct('OriginalFilename', 'Notro.exe'),
        StringStruct('ProductName', 'Notro'),
        StringStruct('ProductVersion', '{__version__}'),
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""

if __name__ == "__main__":
    with open("version_info.txt", "w", encoding="utf-8") as f:
        f.write(VERSION_INFO)
    print("version_info.txt written for Notro", __version__)
