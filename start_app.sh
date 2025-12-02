#!/bin/bash

# セキュリティチェックAI起動スクリプト (Mac/Linux用)

echo "セキュリティチェックAIを起動しています..."
echo ""

# 仮想環境をアクティベート
source .venv/bin/activate

# Streamlitアプリを起動
streamlit run app.py
