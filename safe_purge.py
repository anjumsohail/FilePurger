#!/usr/bin/env python3
# pip install psutil
import os
import shutil
import logging
import argparse
import string
import datetime
import psutil

# =====================
# CONFIGURATION
# =====================
#PROGRAM_DATA_DIR = os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), "FilePurger")
PROGRAM_DATA_DIR = r"C:\FilePurger"
QUARANTINE_DIR = os.path.join(PROGRAM_DATA_DIR, "Quarantine")
LOG_DIR = os.path.join(PROGRAM_DATA_DIR, "logs")

os.makedirs(QUARANTINE_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# File categories
FILE_CATEGORIES = {
    "documents": [".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".pdf", ".csv",".rtf"],
    "videos": [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".m4v", ".3gp", ".flv", ".webm"],
    "images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff",".webp"],
    "archives": [".zip", ".rar", ".7z", ".tar", ".gz"]
    
}
FILE_CATEGORIES["all"] = sorted(set(ext for exts in FILE_CATEGORIES.values() for ext in exts))
	
# Excluded system directories
EXCLUDE_DIRS = [
    r"C:\Windows",
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    r"C:\ProgramData",
    r"C:\Users\All Users",
    r"C:\$Recycle.Bin",
    r"C:\System Volume Information",
    r"D:\Program Files",
    r"D:\Program Files (x86)",
    r"E:\Program Files",
    r"E:\Program Files (x86)",
    r"C:\FilePurger"]

# =====================
# LOGGING
# =====================
scan_log_path = os.path.join(LOG_DIR, f"scan_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
moved_log_path = os.path.join(LOG_DIR, f"moved_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

logging.basicConfig(
    filename=scan_log_path,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

moved_logger = logging.getLogger("moved_files")
moved_handler = logging.FileHandler(moved_log_path)
moved_handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
moved_logger.addHandler(moved_handler)
moved_logger.setLevel(logging.INFO)

# =====================
# FUNCTIONS
# =====================
def is_excluded(path):
    abs_path = os.path.abspath(path)
    for excl in EXCLUDE_DIRS:
        try:
            if os.path.commonpath([abs_path, excl]) == excl:
                return True
        except ValueError:
            continue
    return False

def get_all_drives():
    return [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]

def log_disk_usage():
    logging.info("=== Disk Usage ===")
    print("=== Disk Usage ===")
    for drive in get_all_drives():
        try:
            usage = psutil.disk_usage(drive)
            logging.info(f"{drive} - Total: {usage.total // (1024**3)} GB, Used: {usage.used // (1024**3)} GB, Free: {usage.free // (1024**3)} GB")
            print(f"{drive} - Total: {usage.total // (1024**3)} GB, Used: {usage.used // (1024**3)} GB, Free: {usage.free // (1024**3)} GB")
        except Exception as e:
            logging.warning(f"Could not get usage for {drive}: {e}")

def purge_files(categories, retention_days, dry_run):
    now = datetime.datetime.now()
    extensions = []
    for cat in categories:
        extensions.extend(FILE_CATEGORIES.get(cat, []))

    log_disk_usage()

    for drive in get_all_drives():
        for root, dirs, files in os.walk(drive):
            if is_excluded(root):
                dirs[:] = []  # skip deeper in excluded paths
                continue

            for file in files:
                file_path = os.path.join(root, file)
                if extensions and not file.lower().endswith(tuple(extensions)):
                    continue

                try:
                    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
                    age_days = (now - mtime).days
                    if age_days >= retention_days:
                        logging.info(f"[MATCH] {file_path} ({age_days} days old)")
                        print(f"[MATCH] {file_path} ({age_days} days old)")
                        if not dry_run:
                            dest_path = os.path.join(QUARANTINE_DIR, os.path.relpath(file_path, drive))
                            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                            shutil.move(file_path, dest_path)
                            moved_logger.info(f"{file_path} -> {dest_path}")
                    else:
                        logging.info(f"[SKIP] {file_path} ({age_days} days old)")
                        print(f"[SKIP] {file_path} ({age_days} days old)")
                except Exception as e:
                    logging.error(f"Error processing {file_path}: {e}")
                    print(f"Error processing {file_path}: {e}")

    log_disk_usage()

# =====================
# MAIN
# =====================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Safe file purger with quarantine")
    parser.add_argument("--category", type=str, default="documents,videos",
                        help="Comma-separated categories (documents,videos,images)")
    parser.add_argument("--retention-days", type=int, default=30, help="Retention period in days")
    parser.add_argument("--dry-run", action="store_true", help="Scan only, no file moves")
    args = parser.parse_args()

    categories = [c.strip().lower() for c in args.category.split(",") if c.strip()]
    purge_files(categories, args.retention_days, args.dry_run)

    print(f"\nScan complete. Full log: {scan_log_path}")
    print(f"Moved files log: {moved_log_path}")

# -------------------------------------------------------------------------
# python safe_purge.py --category documents,videos,images --retention-days 1
# retention days 1  Files of today will be skipped and 0 means all files included
#----------------------------------------------------------