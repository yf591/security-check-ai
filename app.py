"""
セキュリティチェックAI - Streamlitアプリケーション
営業向けセキュリティ診断支援ツール
"""

import os
import sys
from pathlib import Path
import logging
from datetime import datetime

import streamlit as st
import pandas as pd
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
sys.path.append(str(Path(__file__).parent))

from src.document_processor import DocumentProcessor, process_directory
from src.vector_database import VectorDatabase, build_database_from_directory

# 環境変数の読み込み
load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 設定
VECTORDB_PATH = os.getenv("VECTORDB_PATH", "./vectordb")
RAW_DATA_DIR = os.getenv("RAW_DATA_DIR", "./data/raw")
PROCESSED_DATA_DIR = os.getenv("PROCESSED_DATA_DIR", "./data/processed")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# ページ設定
st.set_page_config(
    page_title="セキュリティチェックAI",
    page_icon="🔒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# セッション状態の初期化
if "vectordb" not in st.session_state:
    st.session_state.vectordb = None
if "qa_history" not in st.session_state:
    st.session_state.qa_history = []


def init_vectordb():
    """ベクトルデータベースの初期化"""
    if st.session_state.vectordb is None:
        with st.spinner("データベースを読み込み中..."):
            st.session_state.vectordb = VectorDatabase(
                persist_directory=VECTORDB_PATH, embedding_model=EMBEDDING_MODEL
            )
    return st.session_state.vectordb


def main():
    """メインアプリケーション"""

    st.title("🔒 セキュリティチェックAI")
    st.markdown("営業向けセキュリティ診断支援システム")

    # サイドバー
    with st.sidebar:
        st.header("📚 データ管理")

        # データベース統計
        vectordb = init_vectordb()
        stats = vectordb.get_stats()

        st.metric("登録済みQ&A件数", stats["total_qa_pairs"])

        st.divider()

        # データベース構築
        st.subheader("データベース構築")

        uploaded_files = st.file_uploader(
            "ファイルをアップロード",
            type=["pdf", "docx", "xlsx", "xls", "txt", "csv"],
            accept_multiple_files=True,
            help="PDF、Word、Excel、テキストファイルに対応",
        )

        if uploaded_files:
            if st.button("📥 ファイルを処理してDBに追加", type="primary"):
                process_uploaded_files(uploaded_files, vectordb)

        st.divider()

        # ディレクトリから一括構築
        if st.button("🔄 data/rawから再構築"):
            rebuild_database(vectordb)

        if stats["total_qa_pairs"] > 0:
            if st.button("🗑️ データベースをクリア", type="secondary"):
                with st.spinner("データベースをクリア中..."):
                    vectordb.clear_database()
                    st.success("データベースをクリアしました")
                    st.rerun()

    # メインコンテンツ
    tab1, tab2, tab3 = st.tabs(["🔍 質問検索", "📝 一括質問処理", "📊 履歴"])

    with tab1:
        single_question_tab(vectordb)

    with tab2:
        batch_question_tab(vectordb)

    with tab3:
        history_tab()


def single_question_tab(vectordb: VectorDatabase):
    """単一質問タブ"""
    st.header("質問を入力")

    col1, col2 = st.columns([3, 1])

    with col1:
        query = st.text_area(
            "セキュリティチェックに関する質問を入力してください",
            height=150,
            placeholder="例: データの暗号化方法について教えてください",
        )

    with col2:
        top_k = st.slider("検索結果数", 1, 10, 3)
        score_threshold = st.slider("類似度閾値", 0.0, 1.0, 0.5, 0.05)

    if st.button("🔍 検索", type="primary", disabled=not query):
        search_and_display(vectordb, query, top_k, score_threshold)


def batch_question_tab(vectordb: VectorDatabase):
    """一括質問処理タブ"""
    st.header("一括質問処理")

    st.markdown(
        """
    複数の質問を一度に処理します。以下のいずれかの方法で質問を入力してください:
    - テキストエリアに質問を入力（1行1質問）
    - CSVファイルをアップロード（質問列を含む）
    """
    )

    input_method = st.radio("入力方法", ["テキスト入力", "CSVファイル"])

    questions = []

    if input_method == "テキスト入力":
        batch_text = st.text_area(
            "質問を入力（1行に1つの質問）",
            height=200,
            placeholder="データの暗号化方法について\nアクセス制御の設定方法\n...",
        )
        if batch_text:
            questions = [q.strip() for q in batch_text.split("\n") if q.strip()]

    else:
        uploaded_file = st.file_uploader(
            "CSVファイルをアップロード",
            type=["csv"],
            help="質問が含まれる列があるCSVファイル",
        )

        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            st.write("アップロードされたファイルのプレビュー:")
            st.dataframe(df.head())

            question_col = st.selectbox("質問が含まれる列を選択", df.columns)

            if question_col:
                questions = df[question_col].dropna().tolist()

    if questions:
        st.info(f"📝 {len(questions)}件の質問が入力されました")

        col1, col2 = st.columns(2)
        with col1:
            top_k = st.slider("各質問の検索結果数", 1, 5, 1, key="batch_topk")
        with col2:
            score_threshold = st.slider(
                "類似度閾値", 0.0, 1.0, 0.6, 0.05, key="batch_threshold"
            )

        if st.button("🚀 一括検索", type="primary"):
            batch_search_and_display(vectordb, questions, top_k, score_threshold)


def history_tab():
    """履歴タブ"""
    st.header("検索履歴")

    if not st.session_state.qa_history:
        st.info("まだ検索履歴がありません")
        return

    # 履歴をDataFrameに変換
    history_df = pd.DataFrame(st.session_state.qa_history)

    st.dataframe(history_df, use_container_width=True, hide_index=True)

    # CSV出力
    if st.button("📥 履歴をCSVでダウンロード"):
        csv = history_df.to_csv(index=False, encoding="utf-8-sig")
        st.download_button(
            label="ダウンロード",
            data=csv,
            file_name=f"security_check_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )

    if st.button("🗑️ 履歴をクリア"):
        st.session_state.qa_history = []
        st.rerun()


def search_and_display(
    vectordb: VectorDatabase, query: str, top_k: int, score_threshold: float
):
    """検索を実行して結果を表示"""
    with st.spinner("検索中..."):
        results = vectordb.search(query, top_k=top_k, score_threshold=score_threshold)

    if not results:
        st.warning("該当する回答が見つかりませんでした。質問を変えて試してください。")
        return

    st.success(f"✅ {len(results)}件の回答が見つかりました")

    for i, result in enumerate(results, 1):
        with st.expander(
            f"📄 回答 {i} - 類似度: {result['score']:.2%}", expanded=(i == 1)
        ):
            st.markdown(f"**質問:** {result['question']}")
            st.markdown(f"**回答:**")
            st.info(result["answer"])
            st.caption(f"出典: {result['source']}")

            # 履歴に追加
            st.session_state.qa_history.append(
                {
                    "タイムスタンプ": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "検索クエリ": query,
                    "マッチした質問": result["question"],
                    "回答": result["answer"],
                    "類似度": f"{result['score']:.2%}",
                    "出典": result["source"],
                }
            )


def batch_search_and_display(
    vectordb: VectorDatabase, questions: list, top_k: int, score_threshold: float
):
    """一括検索を実行"""
    results_list = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, question in enumerate(questions):
        status_text.text(f"処理中: {i+1}/{len(questions)}")
        progress_bar.progress((i + 1) / len(questions))

        results = vectordb.search(
            question, top_k=top_k, score_threshold=score_threshold
        )

        if results:
            best_result = results[0]
            results_list.append(
                {
                    "質問": question,
                    "マッチした質問": best_result["question"],
                    "回答": best_result["answer"],
                    "類似度": f"{best_result['score']:.2%}",
                    "出典": best_result["source"],
                }
            )

            # 履歴に追加
            st.session_state.qa_history.append(
                {
                    "タイムスタンプ": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "検索クエリ": question,
                    "マッチした質問": best_result["question"],
                    "回答": best_result["answer"],
                    "類似度": f"{best_result['score']:.2%}",
                    "出典": best_result["source"],
                }
            )
        else:
            results_list.append(
                {
                    "質問": question,
                    "マッチした質問": "該当なし",
                    "回答": "該当する回答が見つかりませんでした",
                    "類似度": "0%",
                    "出典": "-",
                }
            )

    status_text.empty()
    progress_bar.empty()

    st.success(f"✅ {len(questions)}件の質問を処理しました")

    # 結果をDataFrameで表示
    results_df = pd.DataFrame(results_list)
    st.dataframe(results_df, use_container_width=True, hide_index=True)

    # CSV出力
    csv = results_df.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        label="📥 結果をCSVでダウンロード",
        data=csv,
        file_name=f"security_check_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )


def process_uploaded_files(uploaded_files, vectordb: VectorDatabase):
    """アップロードされたファイルを処理"""
    processor = DocumentProcessor()
    all_qa_pairs = []

    with st.spinner("ファイルを処理中..."):
        for uploaded_file in uploaded_files:
            # 一時ファイルとして保存
            temp_path = Path(RAW_DATA_DIR) / uploaded_file.name
            temp_path.parent.mkdir(parents=True, exist_ok=True)

            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # 処理
            qa_pairs = processor.process_file(str(temp_path))
            all_qa_pairs.extend(qa_pairs)

            st.info(f"✓ {uploaded_file.name}: {len(qa_pairs)}件のQ&Aペアを抽出")

    if all_qa_pairs:
        with st.spinner("データベースに追加中..."):
            count = vectordb.add_qa_pairs(all_qa_pairs)
            st.success(f"🎉 {count}件のQ&Aペアをデータベースに追加しました")
            st.rerun()
    else:
        st.warning("Q&Aペアを抽出できませんでした")


def rebuild_database(vectordb: VectorDatabase):
    """データベースを再構築"""
    with st.spinner("データベースを再構築中..."):
        vectordb.clear_database()

        qa_pairs = process_directory(RAW_DATA_DIR)

        if qa_pairs:
            vectordb.add_qa_pairs(qa_pairs)
            st.success(f"🎉 {len(qa_pairs)}件のQ&Aペアでデータベースを再構築しました")
        else:
            st.warning(f"{RAW_DATA_DIR} にデータが見つかりませんでした")

        st.rerun()


if __name__ == "__main__":
    main()
