# API Documentation - Karaoke Studio

## Base URL
```
http://localhost:5000
```

---

## API Endpoints Reference

### 1. **Get Settings**
```
GET /api/settings
```
**Description:** Retrieve all user settings  
**Response:**
```json
{
  "success": true,
  "settings": {
    "theme": "dark",
    "accent_color": "#0f766e",
    "api_endpoint": "http://localhost:5000",
    "sample_rate": "48000",
    "buffer_size": "512",
    "default_model": "htdemucs",
    "show_animations": true,
    "compact_mode": false,
    "max_storage": "1000"
  }
}
```

---

### 2. **Save Settings**
```
POST /api/settings
Content-Type: application/json
```
**Request Body:**
```json
{
  "theme": "dark",
  "accent_color": "#0f766e",
  "sample_rate": "48000",
  "buffer_size": "512",
  "default_model": "htdemucs",
  "show_animations": true,
  "compact_mode": false
}
```
**Response:**
```json
{
  "success": true,
  "settings": { /* saved settings */ }
}
```

---

### 3. **Get Stems (Backing Tracks)**
```
GET /api/stems/<project_id>
```
**Description:** Get all stem files for a project  
**Example:** `GET /api/stems/20260329_212407`

**Response:**
```json
{
  "success": true,
  "stems": {
    "vocals": "/files/projects/20260329_212407/stems/htdemucs/.../vocals.wav",
    "drums": "/files/projects/20260329_212407/stems/htdemucs/.../drums.wav",
    "bass": "/files/projects/20260329_212407/stems/htdemucs/.../bass.wav",
    "other": "/files/projects/20260329_212407/stems/htdemucs/.../other.wav"
  },
  "project": {
    "id": "20260329_212407",
    "name": "song_name",
    "has_recording": true,
    "created_at": "2026-03-29T21:24:55"
  }
}
```

---

### 4. **Save Recording**
```
POST /api/save-recording/<project_id>
Content-Type: multipart/form-data
```
**Description:** Save recorded vocal track  
**Form Data:**
- `recording`: (file) The audio blob from recording

**Example:** `POST /api/save-recording/20260329_212407`

**Response:**
```json
{
  "success": true,
  "file_path": "projects/20260329_212407/recording.wav",
  "message": "Recording saved"
}
```

---

### 5. **Storage Info**
```
GET /api/storage-info
```
**Description:** Get disk usage information  
**Response:**
```json
{
  "success": true,
  "used_mb": 254,
  "project_count": 3,
  "disk_free_gb": 450
}
```

---

### 6. **Clear Cache**
```
POST /api/clear-cache
```
**Description:** Delete temporary files and cache  
**Response:**
```json
{
  "success": true,
  "removed": 5,
  "message": "Cache cleared"
}
```

---

### 7. **Upload Audio**
```
POST /upload
Content-Type: multipart/form-data
```
**Description:** Upload audio file for stem separation  
**Form Data:**
- `file`: (file) Audio file (MP3, WAV, etc.)
- `model`: (optional) Separation model (default: htdemucs)

**Response:**
```json
{
  "success": true,
  "project_id": "20260329_212407",
  "redirect_url": "/mixer/20260329_212407",
  "message": "Audio uploaded and separated"
}
```

---

### 8. **Export Karaoke Track**
```
GET /api/export-karaoke/<project_id>
```
**Description:** Export backing track (without vocals)  
**Example:** `GET /api/export-karaoke/20260329_212407`

**Response:** WAV file (binary) with headers:
```
Content-Type: audio/wav
Content-Disposition: attachment; filename="karaoke_20260329_212407.wav"
```

---

### 9. **Get All Projects**
```
GET /api/projects
```
**Description:** Get list of all projects  
**Response:**
```json
{
  "success": true,
  "projects": [
    {
      "id": "20260329_212407",
      "name": "song_name",
      "has_recording": true,
      "created_at": "2026-03-29T21:24:55",
      "score": null
    }
  ]
}
```

---

### 10. **Serve Files**
```
GET /files/<path>
```
**Description:** Serve audio stems, recordings, etc.  
**Examples:**
- `GET /files/projects/20260329_212407/stems/htdemucs/.../vocals.wav`
- `GET /files/projects/20260329_212407/recording.wav`

**Response:** Binary audio file

---

## Human-Friendly Page Routes (NOT APIs)

These render HTML pages (NOT JSON):

```
GET /                           → Home page (upload)
GET /karaoke/<project_id>       → Karaoke recording page
GET /mixer/<project_id>         → Stem mixer page
GET /compare/<project_id>       → Recording comparison page
GET /projects                   → Projects list page
GET /settings                   → Settings page
```

---

## Summary: Total API Calls Per Page

### **Home Page (/)**
```
0 API calls (just static page)
```

### **Settings Page (/settings)**
```
1. GET /api/settings            ← Load saved settings
2. POST /api/settings           ← Save changes
3. POST /api/clear-cache        ← Optional: clear cache
4. GET /api/storage-info        ← Display disk usage
```
**Total: 1-4 calls**

### **Karaoke Page (/karaoke/{id})**
```
1. GET /api/stems/{id}          ← Load backing track stems
2. GET /files/.../vocals.wav    ← Load audio element
3. GET /files/.../drums.wav     ← Load audio element
4. GET /files/.../bass.wav      ← Load audio element
5. GET /files/.../other.wav     ← Load audio element
6. POST /api/save-recording     ← Save recorded vocal
7. GET /api/export-karaoke      ← Download karaoke track
```
**Total: 1-7 calls** (depends on actions)

### **Mixer Page (/mixer/{id})**
```
1. GET /api/stems/{id}          ← Load stems for mixing
2. GET /api/export-karaoke      ← Export mixed track
```
**Total: 1-2 calls**

### **Projects Page (/projects)**
```
1. GET /api/projects            ← Load project list
```
**Total: 1 call**

---

## Response Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Settings loaded |
| 400 | Bad request | Missing required field |
| 404 | Not found | Project doesn't exist |
| 500 | Server error | Separation failed |

---

## Request/Response Examples

### Example 1: Load Settings
```bash
curl -X GET http://localhost:5000/api/settings
```

### Example 2: Save Settings
```bash
curl -X POST http://localhost:5000/api/settings \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "light",
    "sample_rate": "44100",
    "default_model": "htdemucs"
  }'
```

### Example 3: Get Stems for Karaoke
```bash
curl -X GET http://localhost:5000/api/stems/20260329_212407
```

### Example 4: Upload Audio
```bash
curl -X POST http://localhost:5000/upload \
  -F "file=@song.mp3" \
  -F "model=htdemucs"
```

---

## Using in Postman

Import these endpoints into Postman to test the API.

### Collection Template (JSON)
```json
{
  "info": {
    "name": "Karaoke Studio API",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Get Settings",
      "request": {
        "method": "GET",
        "url": "{{base_url}}/api/settings"
      }
    },
    {
      "name": "Save Settings",
      "request": {
        "method": "POST",
        "url": "{{base_url}}/api/settings",
        "body": {
          "mode": "raw",
          "raw": "{\"theme\": \"dark\", \"sample_rate\": \"48000\"}"
        }
      }
    }
  ]
}
```

---

