import os
import logging
import tempfile
import subprocess
from typing import List, Dict, Any, Optional
import whisper
import ffmpeg

from config.config import WHISPER_MODEL, CUDA_VISIBLE_DEVICES

logger = logging.getLogger(__name__)

# Set CUDA device if specified
if CUDA_VISIBLE_DEVICES:
    os.environ["CUDA_VISIBLE_DEVICES"] = CUDA_VISIBLE_DEVICES

def download_audio(video_id: str, output_path: Optional[str] = None) -> str:
    """
    Download audio from a YouTube video.
    
    Args:
        video_id: YouTube video ID
        output_path: Path to save the audio file (optional)
        
    Returns:
        Path to the downloaded audio file
    """
    if not output_path:
        # Create a temporary file
        fd, output_path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
    
    video_url = f"https://www.youtube.com/watch?v={video_id}"
    
    try:
        # Use youtube-dl via subprocess to download audio
        # Note: This requires youtube-dl to be installed
        cmd = [
            "youtube-dl",
            "-x",  # Extract audio
            "--audio-format", "mp3",
            "--audio-quality", "0",  # Best quality
            "-o", output_path,
            video_url
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        return output_path
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to download audio: {e}")
        if os.path.exists(output_path):
            os.unlink(output_path)
        raise

def transcribe_audio(audio_path: str, language: str = "ja") -> List[Dict[str, Any]]:
    """
    Transcribe audio using Whisper.
    
    Args:
        audio_path: Path to audio file
        language: Language code
        
    Returns:
        List of subtitle segments with start time, end time, and text
    """
    try:
        # Load Whisper model
        model = whisper.load_model(WHISPER_MODEL)
        
        # Transcribe audio
        result = model.transcribe(
            audio_path,
            language=language,
            verbose=False
        )
        
        # Format segments
        segments = []
        for segment in result["segments"]:
            segments.append({
                "start_time": segment["start"],
                "end_time": segment["end"],
                "text": segment["text"].strip(),
                "is_auto_generated": True,
                "language": language
            })
            
        return segments
        
    except Exception as e:
        logger.error(f"Failed to transcribe audio: {e}")
        raise
    finally:
        # Clean up temporary file if it's a temp file
        if audio_path.startswith(tempfile.gettempdir()):
            try:
                os.unlink(audio_path)
            except OSError:
                pass

def transcribe_video(video_id: str, language: str = "ja") -> List[Dict[str, Any]]:
    """
    Download and transcribe a YouTube video.
    
    Args:
        video_id: YouTube video ID
        language: Language code
        
    Returns:
        List of subtitle segments
    """
    logger.info(f"Transcribing video {video_id}")
    
    # Download audio
    audio_path = download_audio(video_id)
    
    # Transcribe audio
    segments = transcribe_audio(audio_path, language)
    
    logger.info(f"Transcribed {len(segments)} segments for video {video_id}")
    
    return segments 