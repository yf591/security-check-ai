# 🔒 セキュリティチェックAI

営業向けセキュリティ診断支援システム - StreamlitベースのRAGアプリケーション

## 📋 概要

セキュリティチェックAIは、営業担当者がセキュリティチェック診断を効率的に行うための支援ツールです。過去のセキュリティチェックシートやQ&Aデータから学習し、新しい質問に対して適切な回答を提案します。

### 主な機能

- 📁 **多様なファイル形式対応**: PDF、Word、Excel、CSV、テキストファイルから自動的にQ&Aペアを抽出
- 🔍 **高速検索**: ベクトルデータベース（ChromaDB）による類似度ベースの検索
- 💻 **CPU動作**: GPUなしで動作する軽量な埋め込みモデルを使用
- 🖥️ **クロスプラットフォーム**: Windows、Mac、Linuxで動作
- 📊 **一括処理**: 複数の質問を一度に処理可能
- 📝 **履歴管理**: 検索履歴の保存とCSVエクスポート

## 🚀 セットアップ

### 前提条件

- Python 3.8以上
- 仮想環境（venv）

### インストール手順

1. **リポジトリをクローン**

```bash
git clone <repository-url>
cd security-check-ai
```

2. **仮想環境を作成**

```bash
# Windowsの場合
python -m venv .venv
.venv\Scripts\activate

# Mac/Linuxの場合
python3 -m venv .venv
source .venv/bin/activate
```

3. **依存パッケージをインストール**

```bash
pip install -r requirements.txt
```

初回起動時、埋め込みモデル（約90MB）が自動的にダウンロードされます。

4. **環境変数を設定（オプション）**

```bash
cp .env.example .env
# 必要に応じて .env ファイルを編集
```

## 📖 使い方

### 1. アプリケーションを起動

```bash
streamlit run app.py
```

ブラウザが自動的に開き、`http://localhost:8501` でアプリケーションにアクセスできます。

### 2. データの準備

#### 方法A: ファイルをアップロード

1. サイドバーの「ファイルをアップロード」からファイルを選択
2. 「ファイルを処理してDBに追加」ボタンをクリック

#### 方法B: data/rawディレクトリに配置

1. `data/raw/` ディレクトリにファイルを配置
2. サイドバーの「data/rawから再構築」ボタンをクリック

#### 対応ファイル形式

- **PDF** (.pdf): テキストを抽出してQ&Aペアを検出
- **Word** (.docx): 本文とテーブルからQ&Aペアを抽出
- **Excel** (.xlsx, .xls): Q&A列を自動検出、またはテキストとして処理
- **CSV** (.csv): Q&A列を自動検出
- **テキスト** (.txt): Q&Aパターンを検出

#### Q&Aフォーマット例

システムは以下のパターンを自動認識します：

```
Q: データの暗号化はどのように行われますか？
A: AES-256暗号化方式を使用しています。

質問: アクセス制御の設定方法は？
回答: ロールベースアクセス制御(RBAC)を採用しています。

【質問】バックアップの頻度は？
【回答】毎日自動バックアップを実施しています。
```

### 3. 質問を検索

#### 単一質問モード

1. 「🔍 質問検索」タブを開く
2. 質問を入力
3. 検索結果数と類似度閾値を調整
4. 「検索」ボタンをクリック

#### 一括質問モード

1. 「📝 一括質問処理」タブを開く
2. テキスト入力またはCSVファイルアップロードを選択
3. 複数の質問を入力
4. 「一括検索」ボタンをクリック
5. 結果をCSVでダウンロード可能

### 4. 履歴の確認

「📊 履歴」タブで過去の検索履歴を確認でき、CSVファイルとしてダウンロードも可能です。

## 📁 プロジェクト構造

```
security-check-ai/
├── app.py                      # メインアプリケーション
├── requirements.txt            # 依存パッケージ
├── .env.example               # 環境変数サンプル
├── .gitignore                 # Git除外設定
├── README.md                  # このファイル
├── data/                      # データディレクトリ
│   ├── raw/                   # 元データ（処理前）
│   └── processed/             # 処理済みデータ
├── src/                       # ソースコード
│   ├── document_processor.py  # ドキュメント処理モジュール
│   └── vector_database.py     # ベクトルDB管理モジュール
└── vectordb/                  # ベクトルデータベース（自動生成）
```

## 🛠️ 技術スタック

- **フロントエンド**: Streamlit
- **ベクトルDB**: ChromaDB
- **埋め込みモデル**: sentence-transformers/all-MiniLM-L6-v2
- **ドキュメント処理**: 
  - pypdf (PDF)
  - python-docx (Word)
  - openpyxl (Excel)
  - pandas (CSV/データ処理)

## 🔧 カスタマイズ

### 埋め込みモデルの変更

`.env` ファイルで別のモデルを指定できます：

```bash
# より高精度なモデル（サイズも大きい）
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-mpnet-base-v2

# より軽量なモデル
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L12-v2
```

### ベクトルDBの場所を変更

```bash
VECTORDB_PATH=./custom_vectordb_path
```

## 📊 パフォーマンス

- **モデルサイズ**: 約90MB
- **検索速度**: 1000件のデータベースで約100-200ms/クエリ（CPU）
- **メモリ使用量**: 約500MB-1GB（モデル読み込み時）

## 🐛 トラブルシューティング

### モジュールが見つからないエラー

```bash
# 仮想環境がアクティブか確認
which python  # Mac/Linux
where python  # Windows

# 仮想環境を再度アクティベート
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate     # Windows

# パッケージを再インストール
pip install -r requirements.txt
```

### データベースが読み込めない

```bash
# データベースをリセット
rm -rf vectordb/  # Mac/Linux
rmdir /s vectordb  # Windows

# アプリケーションを再起動してデータを再登録
```

### 日本語が文字化けする

Windowsの場合、コマンドプロンプトのコードページを変更：

```bash
chcp 65001
```

## 📝 ライセンス

このプロジェクトは社内利用を目的としています。

## 🤝 貢献

バグ報告や機能リクエストは、プロジェクト管理者まで連絡してください。

## 📞 サポート

質問や問題がある場合は、プロジェクト管理者にお問い合わせください。

---

**注意**: 初回起動時は埋め込みモデルのダウンロードに数分かかる場合があります。
