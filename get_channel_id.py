#!/usr/bin/env python
import os
import sys
import argparse
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

def get_channel_id_by_name(api_key, channel_name):
    """
    チャンネル名からチャンネルIDを取得する
    
    Args:
        api_key: YouTube Data API キー
        channel_name: チャンネル名
    
    Returns:
        チャンネルID
    """
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    try:
        # チャンネル名で検索
        search_response = youtube.search().list(
            q=channel_name,
            type='channel',
            part='id',
            maxResults=5
        ).execute()
        
        # 検索結果がない場合
        if not search_response.get('items'):
            print(f"チャンネル '{channel_name}' が見つかりませんでした。")
            return None
        
        # 検索結果を表示
        print(f"'{channel_name}' の検索結果:")
        
        for i, item in enumerate(search_response['items']):
            channel_id = item['id']['channelId']
            
            # チャンネル情報を取得
            channel_response = youtube.channels().list(
                part='snippet',
                id=channel_id
            ).execute()
            
            if channel_response['items']:
                channel_title = channel_response['items'][0]['snippet']['title']
                print(f"{i+1}. {channel_title} (ID: {channel_id})")
            
        # 最初の結果のチャンネルIDを返す
        return search_response['items'][0]['id']['channelId']
        
    except HttpError as e:
        print(f"エラーが発生しました: {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='チャンネル名からYouTubeチャンネルIDを取得します')
    parser.add_argument('channel_name', help='検索するチャンネル名')
    
    args = parser.parse_args()
    
    # APIキーを環境変数から取得
    api_key = os.getenv('YOUTUBE_API_KEY')
    
    if not api_key:
        print("エラー: YOUTUBE_API_KEYが設定されていません。.envファイルを確認してください。")
        sys.exit(1)
    
    channel_id = get_channel_id_by_name(api_key, args.channel_name)
    
    if channel_id:
        print(f"\n最も一致するチャンネルID: {channel_id}")
        print(f"このIDを.envファイルのYOUTUBE_CHANNEL_IDに設定してください。") 