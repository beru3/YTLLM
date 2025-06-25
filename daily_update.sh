#!/bin/bash

# 環境変数の設定
export PYTHONPATH=/Users/kurosaki/Dropbox/004_py/YTLLM

# 作業ディレクトリに移動
cd /Users/kurosaki/Dropbox/004_py/YTLLM

# 仮想環境をアクティベート
source fresh_venv/bin/activate

# 現在の日時をログに記録
echo "=== バッチ処理開始: $(date) ===" >> batch_update.log

# バッチ更新を実行
python -m src.ingestion.batch_update >> batch_update.log 2>&1

# 処理結果をログに記録
if [ $? -eq 0 ]; then
  echo "バッチ処理成功: $(date)" >> batch_update.log
else
  echo "バッチ処理失敗: $(date)" >> batch_update.log
fi

echo "===================================" >> batch_update.log 