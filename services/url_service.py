import os
import re
from datetime import datetime
from werkzeug.utils import secure_filename

def is_youtube_url(url):
    """Check if URL is a YouTube link"""
    youtube_regex = r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
    return re.match(youtube_regex, url) is not None


def download_from_url(url, output_folder):
    """
    Download audio from URL (YouTube or direct audio link)
    
    Args:
        url: The URL to download from
        output_folder: Folder to save the downloaded file
        
    Returns:
        Path to downloaded file or None if failed
    """
    try:
        if is_youtube_url(url):
            return download_from_youtube(url, output_folder)
        else:
            return download_direct_audio(url, output_folder)
    except Exception as e:
        print(f"Error downloading from URL: {e}")
        return None


def download_from_youtube(url, output_folder):
    """
    Download audio from YouTube using yt-dlp
    
    Note: Requires yt-dlp to be installed: pip install yt-dlp
    """
    try:
        import yt_dlp
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }],
            'outtmpl': os.path.join(output_folder, f'{timestamp}_%(title)s.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            # Replace extension with mp3
            filename = os.path.splitext(filename)[0] + '.mp3'
            
            if os.path.exists(filename):
                return filename
            
        return None
        
    except ImportError:
        print("yt-dlp not installed. Install with: pip install yt-dlp")
        return None
    except Exception as e:
        print(f"Error downloading from YouTube: {e}")
        return None


def download_direct_audio(url, output_folder):
    """
    Download audio file directly from URL
    """
    try:
        import requests
        
        # Get filename from URL
        filename = url.split('/')[-1]
        filename = secure_filename(filename)
        
        # Add timestamp to avoid conflicts
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        name, ext = os.path.splitext(filename)
        filename = f"{timestamp}_{name}{ext}"
        
        filepath = os.path.join(output_folder, filename)
        
        # Download file
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        return filepath
        
    except Exception as e:
        print(f"Error downloading direct audio: {e}")
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
