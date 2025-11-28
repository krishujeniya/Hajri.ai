#!/usr/bin/env python3
"""
Backup Utility for Hajri.ai
Creates backups of database and training images
"""

import sys
import shutil
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import Config


def create_backup():
    """Create a timestamped backup of data"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Config.BASE_DIR / "backups" / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📦 Creating backup at: {backup_dir}")
    
    # Backup database
    if Config.DB_FILE.exists():
        shutil.copy2(Config.DB_FILE, backup_dir / "hajri.db")
        print(f"✅ Database backed up")
    else:
        print(f"⚠️  Database not found")
    
    # Backup training images
    if Config.TRAINING_IMAGES_DIR.exists():
        shutil.copytree(
            Config.TRAINING_IMAGES_DIR,
            backup_dir / "training_images",
            dirs_exist_ok=True
        )
        print(f"✅ Training images backed up")
    else:
        print(f"⚠️  Training images not found")
    
    # Backup models
    if Config.MODELS_DIR.exists():
        shutil.copytree(
            Config.MODELS_DIR,
            backup_dir / "models",
            dirs_exist_ok=True
        )
        print(f"✅ Models backed up")
    
    print(f"\n✅ Backup complete: {backup_dir}")
    return backup_dir


def main():
    """Main backup function"""
    print("🔄 Hajri.ai Backup Utility\n")
    
    try:
        backup_path = create_backup()
        print(f"\n📁 Backup saved to: {backup_path}")
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
