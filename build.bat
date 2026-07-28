@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [1/3] 의존성 설치...
pip install --upgrade pyinstaller -r requirements.txt || goto :error
echo [2/3] EXE 빌드...
python build_version_file.py || goto :error
rem --collect-all webview가 numpy(28MB)·cryptography(9.5MB)까지 끌어온다. 앱은 둘 다
rem 쓰지 않는다(둘을 import 불가로 막고 PIL·pystray·pywebview 경로를 모두 검증함).
rem 빼면 설치 크기가 절반 가까이 줄고 백신 오탐 표면도 함께 줄어든다.
pyinstaller --onedir --noconsole --name Notro --clean ^
  --icon assets\notro.ico ^
  --version-file version_info.txt ^
  --add-data "notro_app\picker\ui;notro_app/picker/ui" ^
  --exclude-module numpy --exclude-module cryptography ^
  --collect-all webview notro.py || goto :error
echo [3/3] 완료! 결과물: dist\Notro.exe
echo 실행하면 트레이에 상주합니다. 피커 단축키: Ctrl+Shift+E
pause
exit /b 0
:error
echo 빌드 실패. Python과 pip가 설치되어 있는지 확인하세요.
pause
exit /b 1
