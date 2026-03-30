"""
================================================================================
KARAOKE STUDIO - URL DOWNLOAD SERVICE
================================================================================
Download audio from URLs: YouTube videos or direct audio links.

Features:
1. YOUTUBE DOWNLOAD: Extract audio from YouTube videos (using yt-dlp)
2. DIRECT DOWNLOAD: Download audio files from direct URLs
3. ERROR HANDLING: Graceful fallback if libraries unavailable

Dependencies:
- yt-dlp: Download from YouTube (pip install yt-dlp)
- requests: Download from direct URLs (pip install requests)
- ffmpeg: Convert to MP3 (system binary)

Usage:
    from services.url_service import download_from_url
    audio_path, title = download_from_url(url, 'downloads/')
    # Returns: (file_path, display_title)
================================================================================
"""

import os
import re
from datetime import datetime
from werkzeug.utils import secure_filename


def is_youtube_url(url):
    """
    Check if URL is a YouTube link.
    
    Args:
        url: URL string to check
    
    Returns:
        True if URL matches YouTube patterns, False otherwise
    """
    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
    return re.match(youtube_regex, url) is not None


def download_from_url(url, output_folder):
    """
    Download audio from URL (YouTube or direct link).
    
    Auto-detects URL type and calls appropriate handler.
    
    Args:
        url: URL string (YouTube video link or direct audio file link)
        output_folder: Folder to save downloaded file
    
    Returns:
        Tuple (file_path, title) where:
        - file_path: Path to saved audio file, or None on failure
        - title: Display title (from YouTube), or None for direct downloads
    
    Example:
        audio_path, title = download_from_url('https://www.youtube.com/watch?v=...', 'downloads/')
        # Returns: ('downloads/2024...._song.mp3', 'Song Title')
    """
    try:
        if is_youtube_url(url):
            return download_from_youtube(url, output_folder)
        else:
            path = download_direct_audio(url, output_folder)
            return path, None  # Direct audio has no title
    except Exception as e:
        print(f"[URL Service] Error downloading from URL: {e}")
        return None, None


def download_from_youtube(url, output_folder):
    """
    Download audio from YouTube using yt-dlp library.
    
    PROCESS:
    1. Download best audio quality available from YouTube
    2. Convert to MP3 using ffmpeg (196 kbps)
    3. Track filename and title via hooks
    4. Fallback to scanning folder if filename detection fails
    
    Args:
        url: YouTube video URL
        output_folder: Folder to save MP3 file
    
    Returns:
        Tuple (file_path, title) where:
        - file_path: Path to downloaded MP3, or None on failure
        - title: Video title from YouTube metadata
    
    Dependencies:
        yt-dlp library (pip install yt-dlp)
        ffmpeg system binary
    """
    try:
        import yt_dlp

        os.makedirs(output_folder, exist_ok=True)

        # Use fixed basename to ensure predictable path
        # (avoids title sanitization surprises)
        base        = os.path.join(output_folder, 'yt_audio')
        expected_mp3 = base + '.mp3'

        # Hooks to capture filename and metadata during download
        final_path       = [None]
        info_dict_holder = {}

        def _pp_hook(d):
            """Called after post-processor (ffmpeg conversion) finishes"""
            if d.get('status') == 'finished':
                final_path[0] = d.get('info_dict', {}).get('filepath') or d.get('filename')
                info_dict_holder.update(d.get('info_dict', {}))

        def _dl_hook(d):
            """Called during download progress"""
            if d.get('status') == 'finished' and not final_path[0]:
                final_path[0] = d.get('filename')
                info_dict_holder.update(d.get('info_dict', {}))

        # yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',              # Best audio quality
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',           # MP3 bitrate
            }],
            'outtmpl':             base + '.%(ext)s',
            'quiet':               False,
            'no_warnings':         False,
            'progress_hooks':      [_dl_hook],
            'postprocessor_hooks': [_pp_hook],
        }

        # Download and convert
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Resolve file path using multiple strategies
        resolved = None

        # 1) Trust hook capture first
        if final_path[0] and os.path.exists(final_path[0]):
            resolved = final_path[0]

        # 2) Try expected fixed MP3 path
        if not resolved and os.path.exists(expected_mp3):
            resolved = expected_mp3

        # 3) Scan folder for most recently created audio file
        if not resolved:
            audio_exts = ('.mp3', '.m4a', '.opus', '.webm', '.ogg', '.flac', '.wav')
            candidates = [
                os.path.join(output_folder, f)
                for f in os.listdir(output_folder)
                if f.lower().endswith(audio_exts)
            ]
            if candidates:
                # Pick newest file (most recently downloaded)
                candidates.sort(key=os.path.getmtime, reverse=True)
                resolved = candidates[0]

        if not resolved:
            print('[URL Service] YouTube download produced no audio file.')
            return None, None

        # Extract title from metadata
        title = info_dict_holder.get('title')
        print(f"[URL Service] ✓ Downloaded: {title}")
        return resolved, title

    except ImportError:
        print('[URL Service] yt-dlp not installed. Install with: pip install yt-dlp')
        return None, None
    except Exception as e:
        print(f'[URL Service] Error downloading from YouTube: {e}')
        import traceback
        traceback.print_exc()
        return None, None


def download_direct_audio(url, output_folder):
    """
    Download audio file from direct URL.
    
    For direct links to MP3/WAV files (not YouTube).
    
    PROCESS:
    1. Extract filename from URL
    2. Add timestamp to filename (avoid collisions)
    3. Stream download to file
    4. Return file path
    
    Args:
        url: Direct link to audio file (e.g. https://example.com/song.mp3)
        output_folder: Folder to save file
    
    Returns:
        File path on success, None on failure
    
    Dependencies:
        requests library (pip install requests)
    """
    try:
        import requests
        
        # Extract filename from URL
        filename = url.split('/')[-1]
        filename = secure_filename(filename)
        
        # Add timestamp to filename to avoid collisions
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        filename = f"{timestamp}_{name}{ext}"
        
        filepath = os.path.join(output_folder, filename)
        os.makedirs(output_folder, exist_ok=True)
        
        # Download with streaming (memory-efficient for large files)
        print(f"[URL Service] Downloading: {url}")
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()  # Raise on HTTP error
        
        # Write file in chunks
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size_mb = os.path.getsize(filepath) / 1024 / 1024
        print(f"[URL Service] ✓ Downloaded: {filename} ({file_size_mb:.1f} MB)")
        return filepath
        
    except Exception as e:
        print(f"[URL Service] Error downloading direct audio: {e}")
        return None


def get_video_info(url):
    """
    Get information about a YouTube video without downloading
    
    Returns:
        Dictionary with video info or None if failed
    """
    try:
        import yt_dlp
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            return {
                'title': info.get('title'),
                'duration': info.get('duration'),
                'uploader': info.get('uploader'),
                'thumbnail': info.get('thumbnail'),
                'description': info.get('description'),
            }
            
    except ImportError:
        print("yt-dlp not installed")
        return None
    except Exception as e:
        print(f"Error getting video info: {e}")
        return None
