import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import re
import requests
import html
import xml.etree.ElementTree as ET
import time
import json

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    YOUTUBE_TRANSCRIPT_API_AVAILABLE = True
except ImportError:
    YOUTUBE_TRANSCRIPT_API_AVAILABLE = False
    logging.warning("youtube_transcript_api not installed. Some subtitle features will be limited.")

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
    # Try using youtube_transcript_api first if available (doesn't use API quota)
    if YOUTUBE_TRANSCRIPT_API_AVAILABLE:
        try:
            logger.info(f"Attempting to get subtitles for video {video_id} using youtube_transcript_api")
            
            # Get transcript directly without using the list_transcripts method
            transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=[language_code])
            logger.info(f"Successfully retrieved transcript with youtube_transcript_api: {len(transcript_data)} segments")
            
            # Convert to our format
            subtitles = []
            for item in transcript_data:
                subtitles.append({
                    "start_time": item["start"],
                    "end_time": item["start"] + item["duration"],
                    "text": item["text"],
                    "is_auto_generated": True,  # Default to True as we can't easily determine this
                    "language": language_code
                })
            
            return subtitles
            
        except Exception as e:
            logger.warning(f"Failed to get subtitles with youtube_transcript_api: {e}")
            
            # Try with English if Japanese failed
            if language_code != "en":
                try:
                    logger.info(f"Trying to get English subtitles instead")
                    transcript_data = YouTubeTranscriptApi.get_transcript(video_id, languages=["en"])
                    logger.info(f"Successfully retrieved English transcript: {len(transcript_data)} segments")
                    
                    subtitles = []
                    for item in transcript_data:
                        subtitles.append({
                            "start_time": item["start"],
                            "end_time": item["start"] + item["duration"],
                            "text": item["text"],
                            "is_auto_generated": True,
                            "language": "en"
                        })
                    
                    return subtitles
                except Exception as e2:
                    logger.warning(f"Failed to get English subtitles: {e2}")
            
            # Fall back to other methods
    
    # Try using YouTube API if transcript API failed
    try:
        youtube = build_youtube_client()
        
        # Get available caption tracks
        logger.info(f"Attempting to get caption tracks for video {video_id} using YouTube API")
        caption_response = youtube.captions().list(
            part="snippet",
            videoId=video_id
        ).execute()
        
        captions = caption_response.get("items", [])
        logger.info(f"Found {len(captions)} caption tracks for video {video_id}")
        
        # Find the right language track
        target_caption = None
        for caption in captions:
            logger.info(f"Caption track: {caption['snippet']['language']} - {caption['snippet'].get('trackKind', 'unknown')}")
            if caption["snippet"]["language"] == language_code:
                target_caption = caption
                break
        
        if not target_caption:
            logger.warning(f"No {language_code} subtitles found for video {video_id}")
            # Try to find any caption track if specific language not found
            if captions:
                target_caption = captions[0]
                logger.info(f"Using {target_caption['snippet']['language']} caption track instead")
            else:
                return []
        
        # Since YouTube API's captions.download requires OAuth2 authentication,
        # we'll use an alternative method to fetch the captions using the video URL
        return get_subtitles_from_video(video_id, language_code)
        
    except HttpError as e:
        logger.error(f"YouTube API error: {e}")
        # Try alternative method if API fails
        return get_subtitles_from_video(video_id, language_code)

def get_subtitles_from_video(video_id: str, language_code: str = "ja") -> List[Dict[str, Any]]:
    """
    Get subtitles for a video using an alternative method.
    
    Args:
        video_id: YouTube video ID
        language_code: Language code for subtitles
        
    Returns:
        List of subtitle items with start time, end time, and text
    """
    try:
        # First, get the video page to extract the caption track URL
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        logger.info(f"Fetching video page: {video_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(video_url, headers=headers)
        response.raise_for_status()
        
        # Try to find the caption track URL in the page source
        html_content = response.text
        
        # Debug: Save a sample of the HTML content to check
        logger.debug(f"HTML content sample: {html_content[:500]}...")
        
        # Look for the timedtext URL using different patterns
        patterns = [
            r'"captionTracks":\[\{"baseUrl":"(https://www.youtube.com/api/timedtext[^"]*)"',
            r'"playerCaptionsTracklistRenderer":\s*{.*?"captionTracks":\s*\[\s*{"baseUrl":\s*"([^"]+)"',
            r'captionTracks\\"\s*:\s*\[\s*{\s*\\"\s*baseUrl\\"\s*:\s*\\"([^"]+)\\"'
        ]
        
        caption_url = None
        for pattern in patterns:
            match = re.search(pattern, html_content, re.DOTALL)
            if match:
                caption_url = match.group(1).replace("\\u0026", "&")
                logger.info(f"Found caption URL with pattern {patterns.index(pattern)}")
                break
        
        if not caption_url:
            logger.warning(f"Could not find caption track URL for video {video_id}")
            return []
        
        logger.info(f"Caption URL: {caption_url}")
        
        # If language_code is specified, try to find the URL for that language
        if language_code:
            pattern = r'"captionTracks":\[(.*?)\]'
            caption_tracks_match = re.search(pattern, html_content, re.DOTALL)
            
            if caption_tracks_match:
                caption_tracks = caption_tracks_match.group(1)
                lang_pattern = rf'"languageCode":"{language_code}".*?"baseUrl":"(https://www.youtube.com/api/timedtext[^"]*)"'
                lang_match = re.search(lang_pattern, caption_tracks)
                
                if lang_match:
                    caption_url = lang_match.group(1).replace("\\u0026", "&")
                    logger.info(f"Found caption URL for language {language_code}")
        
        # Download the caption file
        logger.info(f"Downloading captions from: {caption_url}")
        response = requests.get(caption_url, headers=headers)
        response.raise_for_status()
        
        content_type = response.headers.get('Content-Type', '')
        logger.info(f"Caption content type: {content_type}")
        
        # Save the raw response for debugging
        with open(f"caption_response_{video_id}.txt", "w", encoding="utf-8") as f:
            f.write(response.text)
        
        # Parse the XML content
        subtitles = parse_youtube_caption_xml(response.text)
        logger.info(f"Parsed {len(subtitles)} subtitle segments")
        return subtitles
        
    except Exception as e:
        logger.error(f"Error getting subtitles for video {video_id}: {e}", exc_info=True)
        return []

def parse_youtube_caption_xml(xml_content: str) -> List[Dict[str, Any]]:
    """
    Parse YouTube caption XML content.
    
    Args:
        xml_content: XML content from YouTube caption track
        
    Returns:
        List of subtitle items with start time, end time, and text
    """
    try:
        # Check if the content is empty
        if not xml_content.strip():
            logger.warning("Empty XML content received")
            return []
        
        logger.debug(f"XML content sample: {xml_content[:500]}...")
        
        root = ET.fromstring(xml_content)
        subtitles = []
        
        for text_element in root.findall(".//text"):
            start_time = float(text_element.get("start", "0"))
            duration = float(text_element.get("dur", "0"))
            end_time = start_time + duration
            
            # Get the text content and decode HTML entities
            text = text_element.text or ""
            text = html.unescape(text)
            
            subtitles.append({
                "start_time": start_time,
                "end_time": end_time,
                "text": text,
                "is_auto_generated": True,  # Assuming auto-generated; hard to determine from XML
                "language": "ja"  # Default to Japanese
            })
        
        return subtitles
        
    except Exception as e:
        logger.error(f"Error parsing YouTube caption XML: {e}", exc_info=True)
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