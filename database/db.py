import sqlite3
import json
from datetime import datetime
import os

DATABASE_FILE = 'karaoke_studio.db'


def get_db_connection():
    """Create database connection"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database with tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Projects table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            original_file TEXT NOT NULL,
            output_folder TEXT NOT NULL,
            model TEXT NOT NULL,
            source TEXT DEFAULT 'file',
            source_url TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            favorite INTEGER DEFAULT 0,
            status TEXT DEFAULT 'completed',
            metadata TEXT
        )
    ''')
    
    # Recordings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recordings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            recording_path TEXT NOT NULL,
            created_at TEXT NOT NULL,
            duration REAL,
            score INTEGER,
            analysis_data TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        )
    ''')
    
    # Settings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()


def save_project(project_data):
    """Save a new project"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO projects (name, original_file, output_folder, model, source, source_url, created_at, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        project_data.get('name'),
        project_data.get('original_file'),
        project_data.get('output_folder'),
        project_data.get('model', 'htdemucs'),
        project_data.get('source', 'file'),
        project_data.get('source_url'),
        project_data.get('created_at', datetime.now().isoformat()),
        project_data.get('status', 'completed')
    ))
    
    project_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return project_id


def get_all_projects(limit=100, offset=0, filter_by=None, sort_by=None):
    """Get all projects with optional filtering and sorting"""
    conn = get_db_connection()
    
    query = 'SELECT * FROM projects'
    params = []
    
    # Add filters
    if filter_by == 'favorites':
        query += ' WHERE favorite = 1'
    elif filter_by == 'in-progress':
        query += ' WHERE status = "in-progress"'
    elif filter_by == 'completed':
        query += ' WHERE status = "completed"'
    
    # Add sorting
    if sort_by == 'name':
        query += ' ORDER BY name ASC'
    elif sort_by == 'size':
        query += ' ORDER BY id DESC'  # placeholder
    elif sort_by == 'rating':
        query += ' ORDER BY id DESC'  # placeholder
    else:  # default: recent
        query += ' ORDER BY created_at DESC'
    
    query += f' LIMIT {limit} OFFSET {offset}'
    
    cursor = conn.cursor()
    cursor.execute(query, params)
    
    projects = []
    for row in cursor.fetchall():
        projects.append(dict(row))
    
    conn.close()
    return projects


def get_project(project_id):
    """Get a specific project by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
    row = cursor.fetchone()
    
    conn.close()
    
    if row:
        return dict(row)
    return None


def update_project(project_id, updates):
    """Update project data"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates['updated_at'] = datetime.now().isoformat()
    
    set_clause = ', '.join([f'{key} = ?' for key in updates.keys()])
    values = list(updates.values()) + [project_id]
    
    cursor.execute(f'UPDATE projects SET {set_clause} WHERE id = ?', values)
    
    conn.commit()
    conn.close()
    
    return cursor.rowcount > 0


def delete_project(project_id):
    """Delete a project"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get project data first to delete files
    cursor.execute('SELECT * FROM projects WHERE id = ?', (project_id,))
    project = cursor.fetchone()
    
    if project:
        # Delete from database
        cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
        conn.commit()
        
        # Optional: Delete associated files
        try:
            if os.path.exists(project['original_file']):
                os.remove(project['original_file'])
            # You might want to delete the output folder too
        except Exception as e:
            print(f"Error deleting files: {e}")
    
    conn.close()
    return project is not None


def save_recording(recording_data):
    """Save a recording"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO recordings (project_id, recording_path, created_at, duration, score, analysis_data)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        recording_data.get('project_id'),
        recording_data.get('recording_path'),
        recording_data.get('created_at', datetime.now().isoformat()),
        recording_data.get('duration'),
        recording_data.get('score'),
        json.dumps(recording_data.get('analysis_data')) if recording_data.get('analysis_data') else None
    ))
    
    recording_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return recording_id


def get_project_recordings(project_id):
    """Get all recordings for a project"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM recordings WHERE project_id = ? ORDER BY created_at DESC', (project_id,))
    
    recordings = []
    for row in cursor.fetchall():
        recording = dict(row)
        if recording.get('analysis_data'):
            recording['analysis_data'] = json.loads(recording['analysis_data'])
        recordings.append(recording)
    
    conn.close()
    return recordings


def toggle_favorite(project_id):
    """Toggle project favorite status"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT favorite FROM projects WHERE id = ?', (project_id,))
    row = cursor.fetchone()
    
    if row:
        new_favorite = 0 if row['favorite'] else 1
        cursor.execute('UPDATE projects SET favorite = ?, updated_at = ? WHERE id = ?',
                      (new_favorite, datetime.now().isoformat(), project_id))
        conn.commit()
    
    conn.close()
    return row is not None
