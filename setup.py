"""
Quick Start Script for AI STEM Karaoke Studio
Initializes database and checks dependencies
"""

import sys
import subprocess
import os

def check_python_version():
    """Check if Python version is 3.11.x"""
    version = sys.version_info
    if version.major == 3 and version.minor == 11:
        print(f"✓ Python version {version.major}.{version.minor}.{version.micro} detected")
        return True
    else:
        print(f"⚠ Warning: Python 3.11.x recommended, you have {version.major}.{version.minor}.{version.micro}")
        return True  # Don't block, just warn

def check_demucs():
    """Check if Demucs is installed"""
    try:
        result = subprocess.run(['demucs', '--help'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Demucs is installed")
            return True
        else:
            print("✗ Demucs not working properly")
            return False
    except FileNotFoundError:
        print("✗ Demucs not found. Install with: pip install demucs")
        return False

def check_flask():
    """Check if Flask is installed"""
    try:
        import flask
        print(f"✓ Flask {flask.__version__} is installed")
        return True
    except ImportError:
        print("✗ Flask not found. Install with: pip install flask")
        return False

def init_database():
    """Initialize the database"""
    try:
        from database.db import init_db
        init_db()
        print("✓ Database initialized successfully")
        return True
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        return False

def create_folders():
    """Create necessary folders"""
    folders = ['uploads', 'separated', 'recordings']
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
    print(f"✓ Created folders: {', '.join(folders)}")
    return True

def main():
    """Main setup function"""
    print("=" * 50)
    print("AI STEM Karaoke Studio - Quick Start")
    print("=" * 50)
    print()
    
    # Run checks
    checks = [
        ("Python Version", check_python_version),
        ("Flask", check_flask),
        ("Demucs", check_demucs),
        ("Folders", create_folders),
        ("Database", init_database),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\nChecking {name}...")
        results.append(check_func())
    
    print("\n" + "=" * 50)
    print("Setup Summary")
    print("=" * 50)
    
    if all(results):
        print("✓ All checks passed! Ready to start.")
        print("\nTo start the application, run:")
        print("  python app.py")
        print("\nThen open your browser to:")
        print("  http://127.0.0.1:5000")
    else:
        print("⚠ Some checks failed. Please fix the issues above.")
        print("\nTo install missing dependencies:")
        print("  pip install -r requirements.txt")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
