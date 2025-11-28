#!/usr/bin/env python3
"""
Hajri.ai Startup Script
Ensures all dependencies are installed and database is initialized before running
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Main startup function"""
    print("🚀 Starting Hajri.ai...")
    
    # Check if database exists
    db_path = Path("assets/hajri.db")
    if not db_path.exists():
        print("📊 Initializing database...")
        try:
            subprocess.run([sys.executable, "scripts/setup_db.py"], check=True)
        except subprocess.CalledProcessError:
            print("⚠️  Database initialization failed, but continuing...")
    
    # Run streamlit
    print("✨ Launching application...")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port=8501",
        "--server.address=0.0.0.0"
    ])

if __name__ == "__main__":
    main()
