#!/bin/bash

# 環境変数の設定
export PYTHONPATH=/Users/kurosaki/Dropbox/004_py/YTLLM

# 作業ディレクトリに移動
cd /Users/kurosaki/Dropbox/004_py/YTLLM

# 仮想環境をアクティベート
source fresh_venv/bin/activate

# 現在の日時をログに記録
echo "=== 過去動画取り込み開始: $(date) ===" >> past_videos_import.log

# 過去動画の取り込み（一度に50件ずつ処理）
python -m src.ingestion.ingest --channel-id UCW3MY7gdx-Gmha9IIx-EGfg --max-videos 50 >> past_videos_import.log 2>&1

# 処理結果をログに記録
if [ $? -eq 0 ]; then
  echo "過去動画取り込み成功: $(date)" >> past_videos_import.log
else
  echo "過去動画取り込み失敗: $(date)" >> past_videos_import.log
fi

# 字幕のプレースホルダーを実際の字幕に更新（一度に50件ずつ処理）
python -m src.ingestion.ingest --update-placeholders --max-videos 50 >> past_videos_import.log 2>&1

# 処理結果をログに記録
if [ $? -eq 0 ]; then
  echo "字幕更新成功: $(date)" >> past_videos_import.log
else
  echo "字幕更新失敗: $(date)" >> past_videos_import.log
fi

# タイムスタンプの更新（一度に50件ずつ処理）
python -m src.ingestion.batch_update --update-timestamps --max 50 >> past_videos_import.log 2>&1

# 処理結果をログに記録
if [ $? -eq 0 ]; then
  echo "タイムスタンプ更新成功: $(date)" >> past_videos_import.log
else
  echo "タイムスタンプ更新失敗: $(date)" >> past_videos_import.log
fi

echo "===================================" >> past_videos_import.log 