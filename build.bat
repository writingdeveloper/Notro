@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [1/3] 의존성 설치...
pip install --upgrade pyinstaller pillow pystray || goto :error
echo [2/3] EXE 빌드...
pyinstaller --onefile --noconsole --name ClipShrink --clean clipshrink.py || goto :error
echo [3/3] 완료! 결과물: dist\ClipShrink.exe
echo 실행하면 트레이에 상주하며 시작 프로그램에 자동 등록됩니다.
pause
exit /b 0
:error
echo 빌드 실패. Python과 pip가 설치되어 있는지 확인하세요.
pause
exit /b 1
