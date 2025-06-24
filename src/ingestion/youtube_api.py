import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.config import (
    YOUTUBE_API_KEY, 
    YOUTUBE_CHANNEL_ID, 
    YOUTUBE_API_SERVICE_NAME, 
    YOUTUBE_API_VERSION
)

logger = logging.getLogger(__name__)

def build_youtube_client():
    """Build and return a YouTube API client."""
    if not YOUTUBE_API_KEY:
        raise ValueError("YouTube API key is not set in environment variables")
    
    return build(
        YOUTUBE_API_SERVICE_NAME,
        YOUTUBE_API_VERSION,
        developerKey=YOUTUBE_API_KEY
    )

def get_channel_videos(
    channel_id: str = YOUTUBE_CHANNEL_ID, 
    max_results: int = 50,
    page_token: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Get videos from a YouTube channel.
    
    Args:
        channel_id: YouTube channel ID
        max_results: Maximum number of results per page
        page_token: Token for the next page of results
        
    Returns:
        Tuple of (list of video items, next page token)
    """
    youtube = build_youtube_client()
    
    # First, get upload playlist ID for the channel
    try:
        channel_response = youtube.channels().list(
            part="contentDetails",
            id=channel_id
        ).execute()
        
        if not channel_response.get("items"):
            logger.error(f"Channel not found: {channel_id}")
            return [], None
            
        uploads_playlist_id = channel_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        
        # Get videos from the uploads playlist
        playlist_response = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=max_results,
            pageToken=page_token
        ).execute()
        
        return playlist_response.get("items", []), playlist_response.get("nextPageToken")
        
    except HttpError as e:
        logger.error(f"YouTube API error: {e}")
        return [], None

def get_video_details(video_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Get detailed information for a list of videos.
    
    Args:
        video_ids: List of YouTube video IDs
        
    Returns:
        List of video details
    """
    if not video_ids:
        return []
        
    youtube = build_youtube_client()
    
    try:
        # Split into chunks of 50 (API limit)
        all_videos = []
        for i in range(0, len(video_ids), 50):
            chunk = video_ids[i:i+50]
            
            response = youtube.videos().list(
                part="snippet,contentDetails,statistics",
                id=",".join(chunk)
            ).execute()
            
            all_videos.extend(response.get("items", []))
            
        return all_videos
        
    except HttpError as e:
        logger.error(f"YouTube API error: {e}")
        return []

def get_video_subtitles(video_id: str, language_code: str = "ja") -> List[Dict[str, Any]]:
    """
    Get subtitles for a video.
    
    Args:
        video_id: YouTube video ID
        language_code: Language code for subtitles
        
    Returns:
        List of subtitle items with start time, end time, and text
    """
    youtube = build_youtube_client()
    
    try:
        # Get available caption tracks
        caption_response = youtube.captions().list(
            part="snippet",
            videoId=video_id
        ).execute()
        
        captions = caption_response.get("items", [])
        
        # Find the right language track
        target_caption = None
        for caption in captions:
            if caption["snippet"]["language"] == language_code:
                target_caption = caption
                break
        
        if not target_caption:
            logger.warning(f"No {language_code} subtitles found for video {video_id}")
            return []
            
        # Download the subtitle track
        # Note: This requires authentication with OAuth 2.0, which is beyond the scope of this example
        # In a real implementation, you would use the captions().download() method
        
        # For this example, we'll return a placeholder
        # In a real implementation, you would parse the subtitle file
        return [
            {
                "start_time": 0.0,
                "end_time": 10.0,
                "text": f"Subtitles would be downloaded here for {video_id}"
            }
        ]
        
    except HttpError as e:
        logger.error(f"YouTube API error: {e}")
        return []

def parse_iso8601_duration(duration: str) -> int:
    """
    Parse ISO 8601 duration format to seconds.
    
    Example: "PT1H22M33S" -> 4953 seconds
    
    Args:
        duration: ISO 8601 duration string
        
    Returns:
        Duration in seconds
    """
    hours = 0
    minutes = 0
    seconds = 0
    
    # Remove PT prefix
    duration = duration[2:]
    
    # Parse hours
    if "H" in duration:
        hours_str, duration = duration.split("H")
        if hours_str:
            hours = int(hours_str)
    
    # Parse minutes
    if "M" in duration:
        minutes_str, duration = duration.split("M")
        if minutes_str:
            minutes = int(minutes_str)
    
    # Parse seconds
    if "S" in duration:
        seconds_str = duration.split("S")[0]
        if seconds_str:
            seconds = int(seconds_str)
    
    return hours * 3600 + minutes * 60 + seconds

def format_video_data(video_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format video data into a standardized structure.
    
    Args:
        video_item: Video data from YouTube API
        
    Returns:
        Formatted video data
    """
    snippet = video_item["snippet"]
    content_details = video_item.get("contentDetails", {})
    statistics = video_item.get("statistics", {})
    
    # Parse published date
    published_at = datetime.fromisoformat(snippet["publishedAt"].replace("Z", "+00:00"))
    
    # Parse duration
    duration_seconds = 0
    if "duration" in content_details:
        duration_seconds = parse_iso8601_duration(content_details["duration"])
    
    return {
        "id": video_item["id"],
        "title": snippet["title"],
        "description": snippet.get("description", ""),
        "published_at": published_at,
        "view_count": int(statistics.get("viewCount", 0)),
        "like_count": int(statistics.get("likeCount", 0)),
        "thumbnail_url": snippet["thumbnails"].get("high", {}).get("url", ""),
        "duration_seconds": duration_seconds,
        "channel_id": snippet["channelId"]
    } 