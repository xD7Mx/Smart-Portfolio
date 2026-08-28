#!/usr/bin/env python3
"""
Smart Portfolio — Backup Script
================================
Creates a complete backup of:
- PostgreSQL database
- Configuration files
- Storage directory
- Reports

Usage: python scripts/backup.py [--type full|db|config]
"""

import os
import sys
import shutil
import tarfile
import subprocess
from datetime import datetime
from pathlib import Path

BASE_DIR   = Path(__file__).parent.parent
BACKUP_DIR = BASE_DIR / "backups"

def create_backup(backup_type: str = "full") -> str:
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"sp_{backup_type}_{timestamp}"
    backup_path = BACKUP_DIR / "manual" / backup_name

    backup_path.mkdir(parents=True, exist_ok=True)
    print(f"📦 Creating {backup_type} backup: {backup_name}")

    # 1. Database dump
    if backup_type in ("full", "db"):
        db_url  = os.getenv("DATABASE_URL", "")
        db_file = backup_path / "database.sql"
        try:
            result = subprocess.run(
                ["pg_dump", db_url, "-f", str(db_file)],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"  ✅ Database dumped: {db_file}")
            else:
                print(f"  ⚠️ Database dump failed: {result.stderr}")
        except FileNotFoundError:
            print("  ⚠️ pg_dump not found — skipping database backup.")

    # 2. Config
    if backup_type in ("full", "config"):
        config_src = BASE_DIR / "config"
        config_dst = backup_path / "config"
        if config_src.exists():
            shutil.copytree(config_src, config_dst)
            print(f"  ✅ Config copied.")

    # 3. Storage
    if backup_type == "full":
        storage_src = BASE_DIR / "storage"
        storage_dst = backup_path / "storage"
        if storage_src.exists():
            shutil.copytree(storage_src, storage_dst, ignore=shutil.ignore_patterns("temp/*"))
            print(f"  ✅ Storage copied.")

    # 4. Compress
    archive_path = str(backup_path) + ".tar.gz"
    with tarfile.open(archive_path, "w:gz") as tar:
        tar.add(backup_path, arcname=backup_name)
    shutil.rmtree(backup_path)

    size_mb = os.path.getsize(archive_path) / (1024 * 1024)
    print(f"  ✅ Archive created: {archive_path} ({size_mb:.2f} MB)")
    return archive_path


def restore_backup(archive_path: str):
    print(f"🔄 Restoring from: {archive_path}")
    restore_dir = BACKUP_DIR / "restore_tmp"
    restore_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive_path, "r:gz") as tar:
        tar.extractall(restore_dir)

    print("  ✅ Archive extracted. Review contents before proceeding.")
    print(f"  📂 Location: {restore_dir}")


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "backup"
    if action == "restore" and len(sys.argv) > 2:
        restore_backup(sys.argv[2])
    else:
        btype = sys.argv[2] if len(sys.argv) > 2 else "full"
        create_backup(btype)
