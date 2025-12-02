"""
ベクトルデータベース管理モジュール
ChromaDBを使用してQ&AペアをベクトルDB化し、類似検索を実行
"""

import os
from typing import List, Dict, Optional
from pathlib import Path
import logging

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorDatabase:
    """ベクトルデータベースの管理クラス"""

    def __init__(
        self,
        persist_directory: str = "./vectordb",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        collection_name: str = "security_qa",
    ):
        """
        初期化

        Args:
            persist_directory: ベクトルDBの保存先ディレクトリ
            embedding_model: 使用する埋め込みモデル（CPU対応の軽量モデル）
            collection_name: コレクション名
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        # ディレクトリ作成
        Path(persist_directory).mkdir(parents=True, exist_ok=True)

        # ChromaDBクライアントの初期化
        self.client = chromadb.PersistentClient(
            path=persist_directory, settings=Settings(anonymized_telemetry=False)
        )

        # 埋め込みモデルの読み込み
        logger.info(f"埋め込みモデルを読み込み中: {embedding_model}")
        self.embedding_model = SentenceTransformer(embedding_model)

        # コレクションの取得または作成
        try:
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(f"既存のコレクション '{collection_name}' を読み込みました")
        except:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "Security check Q&A database"},
            )
            logger.info(f"新しいコレクション '{collection_name}' を作成しました")

    def add_qa_pairs(
        self, qa_pairs: List[Dict[str, str]], batch_size: int = 100
    ) -> int:
        """
        Q&Aペアをベクトルデータベースに追加

        Args:
            qa_pairs: [{"question": "...", "answer": "...", "source": "..."}, ...]
            batch_size: バッチサイズ

        Returns:
            追加された件数
        """
        if not qa_pairs:
            logger.warning("追加するQ&Aペアがありません")
            return 0

        logger.info(f"{len(qa_pairs)}件のQ&Aペアを追加中...")

        documents = []
        metadatas = []
        ids = []

        for i, qa in enumerate(qa_pairs):
            # 質問と回答を組み合わせたテキストを作成
            document = f"質問: {qa['question']}\n回答: {qa['answer']}"
            documents.append(document)

            metadatas.append(
                {
                    "question": qa["question"],
                    "answer": qa["answer"],
                    "source": qa.get("source", "unknown"),
                }
            )

            # 既存のIDとの重複を避けるため、現在のカウントを取得
            current_count = self.collection.count()
            ids.append(f"qa_{current_count + i}")

        # バッチ処理で追加
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            batch_metas = metadatas[i : i + batch_size]
            batch_ids = ids[i : i + batch_size]

            # 埋め込みベクトルを生成
            embeddings = self.embedding_model.encode(batch_docs).tolist()

            # データベースに追加
            self.collection.add(
                embeddings=embeddings,
                documents=batch_docs,
                metadatas=batch_metas,
                ids=batch_ids,
            )

            logger.info(f"進捗: {min(i + batch_size, len(documents))}/{len(documents)}")

        logger.info(f"{len(qa_pairs)}件のQ&Aペアを追加しました")
        return len(qa_pairs)

    def search(
        self, query: str, top_k: int = 5, score_threshold: float = 0.0
    ) -> List[Dict]:
        """
        類似検索を実行

        Args:
            query: 検索クエリ
            top_k: 返す結果の最大数
            score_threshold: スコアの閾値（これ以上のスコアのみ返す）

        Returns:
            [{"question": "...", "answer": "...", "source": "...", "score": 0.9}, ...]
        """
        if self.collection.count() == 0:
            logger.warning("データベースが空です")
            return []

        # クエリの埋め込みベクトルを生成
        query_embedding = self.embedding_model.encode(query).tolist()

        # 類似検索を実行
        results = self.collection.query(
            query_embeddings=[query_embedding], n_results=top_k
        )

        # 結果を整形
        search_results = []

        if results["metadatas"] and len(results["metadatas"][0]) > 0:
            for i, metadata in enumerate(results["metadatas"][0]):
                # ChromaDBは距離を返すので、類似度スコアに変換（1 - distance）
                distance = results["distances"][0][i]
                score = 1 - distance

                if score >= score_threshold:
                    search_results.append(
                        {
                            "question": metadata["question"],
                            "answer": metadata["answer"],
                            "source": metadata["source"],
                            "score": score,
                        }
                    )

        logger.info(f"検索結果: {len(search_results)}件")
        return search_results

    def clear_database(self):
        """データベースをクリア"""
        try:
            self.client.delete_collection(name=self.collection_name)
            logger.info(f"コレクション '{self.collection_name}' を削除しました")

            # 再作成
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Security check Q&A database"},
            )
            logger.info(f"コレクション '{self.collection_name}' を再作成しました")
        except Exception as e:
            logger.error(f"データベースクリアエラー: {str(e)}")

    def get_stats(self) -> Dict:
        """データベースの統計情報を取得"""
        count = self.collection.count()

        return {
            "total_qa_pairs": count,
            "collection_name": self.collection_name,
            "persist_directory": self.persist_directory,
        }


def build_database_from_directory(
    data_directory: str, vectordb_path: str = "./vectordb", clear_existing: bool = False
) -> VectorDatabase:
    """
    データディレクトリからベクトルデータベースを構築

    Args:
        data_directory: データファイルが格納されているディレクトリ
        vectordb_path: ベクトルDBの保存先
        clear_existing: 既存のデータベースをクリアするかどうか

    Returns:
        VectorDatabaseインスタンス
    """
    from document_processor import process_directory

    # ベクトルデータベースの初期化
    vectordb = VectorDatabase(persist_directory=vectordb_path)

    # 既存データをクリア
    if clear_existing:
        vectordb.clear_database()

    # ドキュメントを処理してQ&Aペアを抽出
    qa_pairs = process_directory(data_directory)

    if not qa_pairs:
        logger.warning("Q&Aペアが見つかりませんでした")
        return vectordb

    # ベクトルデータベースに追加
    vectordb.add_qa_pairs(qa_pairs)

    # 統計情報を表示
    stats = vectordb.get_stats()
    logger.info(f"データベース構築完了: {stats}")

    return vectordb


if __name__ == "__main__":
    # テスト用
    print("ベクトルデータベース構築テスト")

    # データベース構築
    vectordb = build_database_from_directory(
        data_directory="./data/raw", vectordb_path="./vectordb", clear_existing=True
    )

    # 検索テスト
    test_query = "セキュリティ対策について教えてください"
    print(f"\n検索クエリ: {test_query}")

    results = vectordb.search(test_query, top_k=3)

    print(f"\n検索結果 ({len(results)}件):")
    for i, result in enumerate(results, 1):
        print(f"\n--- 結果 {i} (スコア: {result['score']:.3f}) ---")
        print(f"質問: {result['question'][:100]}")
        print(f"回答: {result['answer'][:100]}")
        print(f"出典: {result['source']}")
