#!/usr/bin/env python3
"""
Hajri.ai Launcher
Automatically detects uv or virtual environment and launches the application.
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path

def main():
    print("🚀 Initializing Hajri.ai Launcher...")
    
    # 1. Try to use uv (Fastest & Recommended)
    uv_path = shutil.which("uv")
    if uv_path:
        print("⚡ uv detected! Using uv for optimized execution.")
        cmd = ["uv", "run", "streamlit", "run", "src/app.py"]
        
        # On Windows, we need shell=True for some command resolutions, but usually subprocess.run works fine.
        # We use os.execvp on POSIX to replace the process, saving resources.
        if sys.platform != "win32":
            try:
                os.execvp("uv", cmd)
            except OSError as e:
                print(f"⚠️  Failed to exec uv: {e}")
                # Fallback to subprocess if exec fails
                subprocess.run(cmd)
                return
        else:
            subprocess.run(cmd)
            return

    # 2. Fallback: Check for local .venv
    venv_dir = Path.cwd() / ".venv"
    if venv_dir.exists():
        print(f"🐍 Found virtual environment at {venv_dir}")
        
        if sys.platform == "win32":
            python_exe = venv_dir / "Scripts" / "python.exe"
        else:
            python_exe = venv_dir / "bin" / "python"
            
        if python_exe.exists():
            print("✅ Using virtual environment Python.")
            # We use -m streamlit to ensure we use the streamlit installed in that python environment
            cmd = [str(python_exe), "-m", "streamlit", "run", "src/app.py"]
            
            if sys.platform != "win32":
                try:
                    os.execv(str(python_exe), cmd)
                except OSError as e:
                    print(f"⚠️  Failed to exec venv python: {e}")
                    subprocess.run(cmd)
                    return
            else:
                subprocess.run(cmd)
                return
        else:
            print("⚠️  Virtual environment exists but python executable not found.")

    # 3. Last Resort: Use the current running Python
    print("⚠️  No uv or .venv found. Using system Python.")
    print("   (Ensure dependencies are installed: pip install -r requirements.txt)")
    
    cmd = [sys.executable, "-m", "streamlit", "run", "src/app.py"]
    subprocess.run(cmd)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Exiting...")
