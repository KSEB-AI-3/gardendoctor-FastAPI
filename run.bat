@echo off
REM UTF-8 인코딩으로 변경 (한글 깨짐 방지)
chcp 65001 > nul


echo.
echo [INFO] Conda 가상환경을 활성화합니다...
call conda activate ghpark1

echo.
echo [INFO] FastAPI 서버를 시작합니다. (Ctrl+C 로 종료)
uvicorn app.main:app --reload

echo.
echo [INFO] 서버가 종료되었습니다.
pause