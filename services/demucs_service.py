import subprocess
import os

def separate_audio(file_path):
    subprocess.run(["demucs", file_path])

    filename = os.path.splitext(os.path.basename(file_path))[0]
    return f"htdemucs/{filename}"
