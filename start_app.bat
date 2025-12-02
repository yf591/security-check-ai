@echo off
chcp 65001 > nul
echo セキュリティチェックAIを起動しています...
echo.

REM 仮想環境をアクティベート
call .venv\Scripts\activate.bat

REM Streamlitアプリを起動
streamlit run app.py

pause
