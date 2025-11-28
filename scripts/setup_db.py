#!/usr/bin/env python3
"""
Database Setup Script
Initializes the database and creates the default admin user
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import init_database
from src.config.settings import Config


def main():
    """Main setup function"""
    print("🚀 Setting up Hajri.ai database...")
    print(f"📁 Database location: {Config.DB_FILE}")
    
    # Validate configuration
    issues = Config.validate_config()
    if issues:
        print("\n⚠️  Configuration Warnings:")
        for issue in issues:
            print(f"   {issue}")
        print()
    
    # Initialize database
    try:
        init_database()
        print("✅ Database setup complete!")
        print(f"\n📊 Next steps:")
        print(f"   1. Update .env with your credentials")
        print(f"   2. Run: streamlit run app.py")
        print(f"   3. Login with username: {Config.ADMIN_USERNAME}")
        
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
