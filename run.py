#!/usr/bin/env python3
"""
Hajri.ai - One-Command Launcher
Simply run: uv run streamlit run src/app.py
"""

import subprocess
import sys
from pathlib import Path

def main():
    """Launch Hajri.ai with auto-setup"""
    print("🚀 Starting Hajri.ai...")
    
    # Check if database exists, initialize if needed
    db_path = Path("assets/hajri.db")
    if not db_path.exists():
        print("📊 Initializing database...")
        try:
            subprocess.run([sys.executable, "scripts/setup_db.py"], check=True)
            print("✅ Database initialized")
        except subprocess.CalledProcessError:
            print("⚠️  Database initialization failed, continuing...")
    
    # Launch Streamlit
    print("✨ Launching application at http://localhost:8501")
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", "src/app.py",
        "--server.port=8501",
        "--server.address=0.0.0.0"
    ])

if __name__ == "__main__":
    main()
