# 🎵 AI-Powered Stem Separation & Karaoke Studio

A web-based AI music processing platform that performs automatic audio stem separation and provides interactive karaoke and mixing features.

---

## USE Python 3.11.xx Version

---

## 🚀 Project Overview

This project implements a deep learning–based music source separation system using the **Demucs** pre-trained model.  
It allows users to:

- Upload audio files or provide audio URLs
- Automatically separate music into individual stems:
  - Vocals
  - Drums
  - Bass
  - Other instruments
- Generate karaoke (instrumental) versions
- Interactively control stem playback
- Optionally record microphone input for singing along

---

## 🎯 Objectives

- Implement AI-based music source separation
- Develop a Flask-based web application
- Support dual input modes (Upload + URL)
- Provide karaoke generation
- Enable interactive stem mixing
- Integrate optional microphone recording

---

## 🏗️ System Architecture
User
↓
Web Interface (Frontend)
↓
Flask Backend
↓
Demucs AI Model
↓
Separated Audio Stems
↓
Karaoke & Stem Mixer

---

## 🛠️ Tech Stack

- **Backend:** Flask (Python)
- **AI Model:** Demucs (Deep Learning)
- **Frontend:** HTML, CSS, JavaScript
- **Database:** SQLite (Optional)
- **Audio Processing:** FFmpeg
- **URL Processing:** yt-dlp

---

## 📂 Project Structure
ai-stem-karaoke-studio/
│
├── app.py
├── services/
├── database/
├── templates/
├── static/
├── uploads/
└── separated/

---

## ⚙️ Installation & Setup

### 1️⃣ Clone Repository

```bash
git clone <your-repo-url>
cd ai-stem-karaoke-studio
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
http://127.0.0.1:5000
