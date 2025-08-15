import os
import sys
import json
import time
import shutil
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from string import ascii_uppercase

# --------------------------------------------------------------------------------------
# Utility helpers (no external deps; uses stdlib only)
# --------------------------------------------------------------------------------------

SCRIPT_DIR = Path(sys.argv[0]).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
ERROR_LOG_PATH = SCRIPT_DIR / "error.log"

def write_error(msg: str) -> None:
    """Write startup/config errors to error.log in the executable directory and stderr."""
    try:
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} - ERROR - {msg}\n")
            print(f"{datetime.now():%Y-%m-%d %H:%M:%S} - ERROR - {msg}\n")
            
    except Exception:
        pass
    print(f"[ERROR] {msg}", file=sys.stderr)

def human_size(num_bytes: int) -> str:
    units = ["B","KB","MB","GB","TB","PB"]
    n = float(num_bytes)
    for u in units:
        if n < 1024.0:
            return f"{n:.0f} {u}" if u == "B" else f"{n:.0f} {u}"
        n /= 1024.0
    return f"{n:.0f} EB"

def list_fixed_drives() -> list[str]:
    """Return existing drive roots like ['C:\\','D:\\',...]"""
    drives = []
    for letter in ascii_uppercase:
        root = f"{letter}:\\"
        if os.path.exists(root):
            drives.append(root)
    return drives

def disk_usage_safe(root: str):
    """shutil.disk_usage wrapper (works without psutil)."""
    try:
        total, used, free = shutil.disk_usage(root)
        return total, used, free
    except Exception:
        return None

def short_hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="ignore")).hexdigest()[:8]

def same_drive(p1: str, p2: str) -> bool:
    return os.path.splitdrive(p1)[0].lower() == os.path.splitdrive(p2)[0].lower()

def is_under(path: str, prefix: str) -> bool:
    """True if path is under prefix; safe across drives."""
    try:
        if not same_drive(path, prefix):
            return False
        cp = os.path.commonpath([os.path.abspath(path), os.path.abspath(prefix)])
        return cp == os.path.abspath(prefix)
    except Exception:
        return False

def should_exclude_dir(root: str, exclude_dirs: list[str]) -> bool:
    for ex in exclude_dirs:
        if is_under(root, ex):
            return True
    return False

def build_quarantine_dest(quarantine_root: Path, src_path: Path) -> Path:
#   Preserve drive + relative path under quarantine, with short hash to avoid collisions.
#    Example: src: C:\Users\Bob\Docs\report.pdf dest: {Quarantine}\C\Users\Bob\Docs\report__a1b2c3d4.pdf
    drive, _ = os.path.splitdrive(str(src_path))
    drive_letter = (drive.replace(":", "") or "ROOT")
    rel = src_path.relative_to(Path(drive + os.sep))
    base = src_path.stem
    ext = src_path.suffix
    suffix = f"__{short_hash(str(src_path))}{ext}"
    return quarantine_root / drive_letter / rel.parent / (base + suffix)

# --------------------------------------------------------------------------------------
# Config loading & validation
# --------------------------------------------------------------------------------------

REQUIRED_TOP_KEYS = ["PROGRAM_DATA_DIR", "EXCLUDE_DIRS", "FILE_CATEGORIES"]

DEFAULTS_IF_MISSING = {
    "retention_days": 7,
    "dry_run": False,
    "AutoDelete":False,
}

def load_config_or_exit() -> dict:
    if not CONFIG_PATH.exists():
        write_error(f"Config file not found: {CONFIG_PATH}")
        sys.exit(1)

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        write_error(f"Failed to parse config.json: {e}")
        print(f"Failed to parse config.json: {e}")
        
        sys.exit(1)

    # Validate required keys
    for k in REQUIRED_TOP_KEYS:
        if k not in cfg:
            write_error(f"Missing required key in config.json: {k}")
            print(f"Missing required key in config.json: {k}")
            sys.exit(1)

    # Fill defaults for optional keys if missing
    for k, v in DEFAULTS_IF_MISSING.items():
        cfg.setdefault(k, v)

    # Build "all" category automatically (do not require it in config)
    all_exts = set()
    for exts in cfg["FILE_CATEGORIES"].values():
        all_exts.update(ext.lower() for ext in exts)
    cfg["FILE_CATEGORIES"]["all"] = sorted(all_exts)

    return cfg

# --------------------------------------------------------------------------------------
# Logging setup (scan + move logs under PROGRAM_DATA_DIR\Logs)
# --------------------------------------------------------------------------------------

def setup_loggers(program_data_dir: Path):
    logs_dir = program_data_dir / "Logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    scan_log_path = logs_dir / f"scan_log_{ts}.log"
    move_log_path = logs_dir / f"move_log_{ts}.log"

    # Scan logger
    scan_logger = logging.getLogger("scan_logger")
    scan_logger.setLevel(logging.INFO)
    scan_logger.propagate = False
    scan_fh = logging.FileHandler(scan_log_path, mode="w", encoding="utf-8")
    scan_fh.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
    scan_logger.addHandler(scan_fh)
    # Console echo for scan
    scan_ch = logging.StreamHandler(sys.stdout)
    scan_ch.setFormatter(logging.Formatter("%(message)s"))
    scan_logger.addHandler(scan_ch)

    # Move logger
    move_logger = logging.getLogger("move_logger")
    move_logger.setLevel(logging.INFO)
    move_logger.propagate = False
    move_fh = logging.FileHandler(move_log_path, mode="w", encoding="utf-8")
    move_fh.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
    move_logger.addHandler(move_fh)
    # Console echo for moves
    move_ch = logging.StreamHandler(sys.stdout)
    move_ch.setFormatter(logging.Formatter("%(message)s"))
    move_logger.addHandler(move_ch)

    return scan_logger, move_logger

# --------------------------------------------------------------------------------------
# Core scanning & quarantining
# --------------------------------------------------------------------------------------

def run_scan(cfg: dict):
    PROGRAM_DATA_DIR = Path(cfg["PROGRAM_DATA_DIR"])
    QUARANTINE_DIR = PROGRAM_DATA_DIR / "Quarantine"
    LOGS_DIR = PROGRAM_DATA_DIR / "Logs"
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    scan_logger, move_logger = setup_loggers(PROGRAM_DATA_DIR)

    # Effective excludes: user-provided + our own (Quarantine & Logs)
    EXCLUDE_DIRS = [os.path.abspath(p) for p in cfg["EXCLUDE_DIRS"]]
    EXCLUDE_DIRS.extend([
        str(QUARANTINE_DIR.resolve()),
        str(LOGS_DIR.resolve()),
        str(PROGRAM_DATA_DIR.resolve()),
    ])

    # Extensions to include = union of all categories ("all")
    SELECTED_EXTS = set(cfg["FILE_CATEGORIES"]["all"])

    # Header
    scan_logger.info("=" * 80)
    print("=" * 80)
    scan_logger.info(f"START scan | retention_days={cfg['retention_days']} | dry_run={cfg['dry_run']}")
    print(f"START scan | retention_days={cfg['retention_days']} | dry_run={cfg['dry_run']}")
    scan_logger.info(f"ProgramDataDir={PROGRAM_DATA_DIR} | Quarantine={QUARANTINE_DIR} | Logs={LOGS_DIR}")
    print(f"ProgramDataDir={PROGRAM_DATA_DIR} | Quarantine={QUARANTINE_DIR} | Logs={LOGS_DIR}")

    # Disk usage summary
    scan_logger.info("=== Disk Usage ===")
    for drive in list_fixed_drives():
        du = disk_usage_safe(drive)
        if du:
            total, used, free = du
            scan_logger.info(f"{drive} - Total: {human_size(total)}, Used: {human_size(used)}, Free: {human_size(free)}")
            print(f"{drive} - Total: {human_size(total)}, Used: {human_size(used)}, Free: {human_size(free)}")
        else:
            scan_logger.info(f"{drive} - (unavailable)")
            print(f"{drive} - (unavailable)")
    scan_logger.info("-" * 80)

    # Cutoff epoch
    cutoff_epoch = time.time() - (cfg["retention_days"] * 86400)

    # Walk all drives
    for drive in list_fixed_drives():
        for root, dirs, files in os.walk(drive, topdown=True):
            # Prune excluded dirs in-place
            pruned = []
            for d in list(dirs):
                full = os.path.join(root, d)
                if should_exclude_dir(full, EXCLUDE_DIRS):
                    pruned.append(d)
            for d in pruned:
                dirs.remove(d)

            # Echo current directory being scanned
            scan_logger.info(f"[SCAN] {root}")
            print(f"[SCAN] {root}")

            for fname in files:
                fpath = os.path.join(root, fname)
                ext = os.path.splitext(fname)[1].lower()

                if ext not in SELECTED_EXTS:
                    continue

                try:
                    mtime = os.path.getmtime(fpath)
                except FileNotFoundError:
                    scan_logger.info(f"[GONE] {fpath}")
                    print(f"[GONE] {fpath}")
                    continue
                except PermissionError as e:
                    scan_logger.info(f"[DENIED] {fpath} | {e}")
                    print(f"[DENIED] {fpath} | {e}")
                    continue
                except Exception as e:
                    scan_logger.info(f"[ERROR] {fpath} | {e}")
                    print(f"[ERROR] {fpath} | {e}")
                    continue

                age_days = int((time.time() - mtime) // 86400)

                if mtime < cutoff_epoch:
                    # Qualifies by retention age
                    scan_logger.info(f"[MATCH] {fpath} ({age_days} days old)")
                    if not cfg["dry_run"]:
                        try:
                            dest = build_quarantine_dest(QUARANTINE_DIR, Path(fpath))
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            shutil.move(fpath, dest)
                            move_logger.info(f"[MOVE] {fpath} -> {dest} ({age_days} days old)")
                            print(f"[MOVE] {fpath} -> {dest} ({age_days} days old)")
                        except PermissionError as e:
                            scan_logger.info(f"[DENIED] move {fpath} | {e}")
                            print(f"[DENIED] move {fpath} | {e}")
                        except Exception as e:
                            scan_logger.info(f"[ERROR] move {fpath} | {e}")
                            print(f"[ERROR] move {fpath} | {e}")
                else:
                    scan_logger.info(f"[SKIP] {fpath} ({age_days} days old)")
                    print(f"[SKIP] {fpath} ({age_days} days old)")

    scan_logger.info("END scan")
    print("END scan")
    scan_logger.info("=" * 80)
    if cfg["AutoDelete"]:
        clear_directory(QUARANTINE_DIR,scan_logger)

def clear_directory(directory_path, logger):
#Delete all files and subdirectories in the specified directory."""

    if not os.path.isdir(directory_path):
        logger.info(f"Directory not found: {directory_path}")
        raise FileNotFoundError(f"Directory not found: {directory_path}")

    logger.info(f"Clearing directory: {directory_path}")

    for item in os.listdir(directory_path):
        item_path = os.path.join(directory_path, item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
        except Exception as e:
            logger.info(f"Failed to delete {item_path}. Reason: {e}")
            print(f"Failed to delete {item_path}. Reason: {e}")

    logger.info(f"Finished clearing quarantine directory: {directory_path}")

            
# Example usage:
# clear_directory('/path/to/your/directory')
# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------

if __name__ == "__main__":
    cfg = load_config_or_exit()
    run_scan(cfg)
