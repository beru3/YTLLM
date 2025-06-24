# マーケティングLLMシステム

「マーケティング侍」YouTubeチャンネルのコンテンツを活用した、マーケティング知識に特化したRetrieval-Augmented Generation (RAG)ベースのLLMサービスです。

## 概要

このシステムは、マーケティング関連のYouTube動画や関連ドキュメントを処理し、自然言語で検索可能なナレッジデータベースを構築します。DeepSeekのLLMおよび埋め込みAPIを使用して、高品質なマーケティングの洞察と提案を提供します。

## 主な機能

- YouTube動画のメタデータと字幕の抽出
- DeepSeek APIを使用した文字起こしと応答生成
- PDFやGoogleスプレッドシートのドキュメントクローリング
- ChromaDBを使用したベクターベースの意味検索
- DeepSeek Chat APIを活用したRAG応答生成
- 元のコンテンツへのリンク付き出典表示
- 新しいコンテンツの自動日次バッチ更新

## プロジェクト構造

```
├── data/                  # 生データと処理済みデータの保存場所
├── src/                   # ソースコード
│   ├── ingestion/         # データ取り込みコンポーネント
│   ├── processing/        # テキスト処理と埋め込み
│   ├── retrieval/         # ベクター検索と取得
│   ├── generation/        # LLM応答生成
│   ├── api/               # FastAPIエンドポイント
│   └── utils/             # ヘルパー関数
├── tests/                 # テストスイート
├── config/                # 設定ファイル
└── notebooks/             # 開発用ノートブック
```

## セットアップ

1. リポジトリをクローンする
2. 依存関係をインストール: `pip install -r requirements.txt`
3. `.env`ファイルに環境変数を設定（`.env.example`参照）
4. データベースを初期化: `python init_db.py`

## 使い方

### 1. APIサーバーの起動

```
python run_api.py
```

サーバーは http://0.0.0.0:8000 で起動します。バックグラウンドで実行する場合は:

```
python run_api.py &
```

### 2. 質問の実行

```
python test_query.py "あなたの質問"
```

例:
```
python test_query.py "マーケティングとは何ですか？"
python test_query.py "マーケティングの4Pとは何ですか？"
```

### 3. バッチ更新（新しい動画の取得）

```
python -m src.ingestion.batch_update
```

このコマンドで最新の動画コンテンツを取得し、データベースを更新します。

### 4. 環境設定

設定は `.env` ファイルで管理されています。主な設定項目:
- `YOUTUBE_API_KEY`: YouTube API用キー
- `YOUTUBE_CHANNEL_ID`: UCW3MY7gdx-Gmha9IIx-EGfg (マーケティング侍)
- `DEEPSEEK_API_KEY`: DeepSeek API用キー
- `USE_DEEPSEEK`: true (DeepSeek APIを使用するかどうか)

## 開発状況

現在のバージョン: v0.1（ドラフト）
フェーズ: 実装完了

## ライセンス

内部使用のみ。「マーケティング侍」YouTubeチャンネルのすべてのコンテンツはライセンス契約に基づいて使用されています。 