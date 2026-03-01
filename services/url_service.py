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
    Download audio from URL (YouTube or direct audio link).

    Returns:
        Tuple (file_path, display_title) where display_title may be None
        for direct audio downloads.  file_path is None on failure.
    """
    try:
        if is_youtube_url(url):
            return download_from_youtube(url, output_folder)
        else:
            path = download_direct_audio(url, output_folder)
            return path, None
    except Exception as e:
        print(f"Error downloading from URL: {e}")
        return None, None


def download_from_youtube(url, output_folder):
    """
    Download audio from YouTube using yt-dlp.

    Uses a fixed base name ('yt_audio') so the on-disk path is fully
    predictable regardless of video title or OS filename sanitization.
    Falls back to scanning the folder if the expected file isn't found.
    """
    try:
        import yt_dlp

        os.makedirs(output_folder, exist_ok=True)

        # Fixed base name avoids all title-sanitization surprises
        base        = os.path.join(output_folder, 'yt_audio')
        expected_mp3 = base + '.mp3'

        # Track the final filename and title via yt-dlp hooks
        final_path       = [None]
        info_dict_holder = {}

        def _pp_hook(d):
            if d.get('status') == 'finished':
                final_path[0] = d.get('info_dict', {}).get('filepath') or d.get('filename')
                info_dict_holder.update(d.get('info_dict', {}))

        def _dl_hook(d):
            if d.get('status') == 'finished' and not final_path[0]:
                final_path[0] = d.get('filename')
                info_dict_holder.update(d.get('info_dict', {}))

        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl':             base + '.%(ext)s',
            'quiet':               False,
            'no_warnings':         False,
            'progress_hooks':      [_dl_hook],
            'postprocessor_hooks': [_pp_hook],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Resolve path using multiple strategies
        resolved = None

        # 1) Trust the hook result first
        if final_path[0] and os.path.exists(final_path[0]):
            resolved = final_path[0]

        # 2) Expected fixed mp3 path
        if not resolved and os.path.exists(expected_mp3):
            resolved = expected_mp3

        # 3) Scan folder for any audio file that was just created
        if not resolved:
            audio_exts = ('.mp3', '.m4a', '.opus', '.webm', '.ogg', '.flac', '.wav')
            candidates = [
                os.path.join(output_folder, f)
                for f in os.listdir(output_folder)
                if f.lower().endswith(audio_exts)
            ]
            if candidates:
                candidates.sort(key=os.path.getmtime, reverse=True)
                resolved = candidates[0]

        if not resolved:
            print('[url_service] YouTube download produced no audio file.')
            return None, None

        title = info_dict_holder.get('title')
        return resolved, title

    except ImportError:
        print('yt-dlp not installed. Install with: pip install yt-dlp')
        return None, None
    except Exception as e:
        print(f'Error downloading from YouTube: {e}')
        import traceback; traceback.print_exc()
        return None, None


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
