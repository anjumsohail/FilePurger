# 🗑️ FilePurger

**FilePurger** is a safe file purging utility for Windows that scans all drives (or a specific path) for files in selected categories (documents, images, videos, etc.) and moves old files to a quarantine folder instead of deleting them immediately.  
It maintains **two separate logs**:
1. **Scan Log** – All files scanned, skipped, or moved.
2. **Move Log** – Only files that were moved to quarantine.
**Who Need this** Corporates, Cyber Cafes or Educational Institutes that Need to Remove the User Data on Routine Basis for Data Security or Prevent Data breach without Factory Reset or System Format.

---

## 📜 Features
# Version 1
- Scan **all available drives** automatically or a specified path.
- Select category: `documents`, `images`, `videos`, `archives`, or `all`.
- Safe purging — moves files to a **quarantine folder** instead of deleting them.
- **Two log files** for tracking:
  - `scan_log.txt` – Complete scan details.
  - `move_log.txt` – Only moved file details.
- Configurable quarantine location.
- Works on **Windows** with Python or as a standalone `.exe`.
- **Age-based purging** – Deletes files older than the defined retention days.
- **File type filtering** – Can be restricted to certain file extensions (e.g., `.pdf`).
- **Dry-run mode** – Shows what would be deleted without actually deleting anything.
- **Safe logging** – Generates detailed logs of actions taken and skipped files.
- **Retention flexibility** – Set retention days from `0` (delete immediately) upwards.
- **Cross-directory support** – Can purge multiple directories in one run.
# Version 2
- Automatic Execution using by taking parameters from Config.json (Sample included) instead of passing via Environment
- Configration Option of AutoDele, is set to True, will Delete the Quarantined Files Directory as well.
- configuration option to change the Log and Quarantine Files Directory
---

## 📂 Categories & File Types
| Category   | Extensions                                                                 |
|------------|-----------------------------------------------------------------------------|
| documents  | .pdf, .doc, .docx, .xls, .xlsx, .ppt, .pptx, .txt, .csv                     |
| images     | .jpg, .jpeg, .png, .gif, .bmp, .tiff                                        |
| videos     | .mp4, .avi, .mov, .mkv                                                      |
| archives   | .zip, .rar, .7z, .tar, .gz                                                  |
| all        | Combines all above                                                          |

---

## 🖥️ Prerequisites

### **Option 1 – Run with Python**
- **Windows 10/11**
- **Python 3.12+** (official version, not Microsoft Store version)
- `pip` package manager
- Required Python modules:
  ```bash
  pip install psutil
  or 
  Optional: PyInstaller #if you want to create a standalone .exe:
  pip install pyinstaller 
  with
  pip install -r requirements.txt

## Option 2 – Run as Standalone Executable

No Python required

Just download the built FilePurger.exe (see build instructions below)

## 🚀 Usage
# Version 1:
Command-line Options
python safe_purge.py --category documents --retention-days 30 --quarantine "C:\Quarantine"
# Version 2:
Set the Parameters in config.json file first, if need to modify
python auto_purge.py

## 📌 Example Use Cases
- **Corporate data retention** – Automatically remove outdated reports or invoices.
- **Disk space cleanup** – Keep only recent backups, remove older ones.
- **Regulatory compliance** – Maintain only required records.

## Configurations:
# Verion 1
Utility is customizable via following arguments.
- category	File category (documents, images, videos, archives, all)	Required
- retention-days	Move files older than these days	30
- quarantine	Quarantine folder path	C:\FilePurger\Quarantine
- path	Start scanning from this path	All available drives
# Version 2
- **PROGRAM_DATA_DIR**: config.json file Parameter to Set the default directory to store Logs and quarantine Files instead of Fixed C:\FilePurger
- **EXCLUDE_DIRS**: Array of Directories or Drives that are should be excluded from scanning.
- **FILE_CATEGORIES**: Array of File Types that need to scanned for quarantine
- **retention_days**: Age of Files, in Number of Days, above that should be included into the quarantine List
- **dry_run**: Boolean value: if true will scan only and not Quarantine the Files.
- **AutoDelete**: Boolean value, if true will automatically Delete the Quarantined Files.
Example 1 – Scan All Drives for Old PDFs
python safe_purge.py --category documents --retention-days 60
Example 2 – Scan a Specific Folder
python safe_purge.py --category images --retention-days 0 --path "D:\Photos"

## 📄 Log Files
scan_log.txt – Records all scanned files with status:
- [MOVE] – Moved to quarantine.
- [SKIP] – Too new, skipped.
- move_log.txt – Records only moved files (source → destination).
- Logs are saved in: C:\FilePurger\Logs (Note : in Version 1)

## 🛠️ Build Standalone Executable
If you want to make FilePurger.exe so it can run without Python:
- 1️⃣ Install Python (Official Version)
  - Uninstall Microsoft Store Python if installed.
  - Download from python.org – Python 3.12 (64-bit).
- During install:
  - ✅ Add Python to PATH
  - ✅ Install pip
  - 2️⃣ Install PyInstaller
- pip install pyinstaller psutil
- 3️⃣ Build EXE
  - pyinstaller --onefile --noconsole --name FilePurger safe_purge.py
- The EXE will appear in the dist folder.
- 4️⃣ Install to C:\FilePurger
  - Create folder:
  - mkdir C:\FilePurger
  - Copy FilePurger.exe there.
  - Create C:\FilePurger\Logs and C:\FilePurger\Quarantine.
## 💼 Use Cases
- Corporate environments to archive old files from shared drives.
- Personal file cleanup while keeping a recovery option.
- Compliance with data retention policies.
- Preparing drives for reallocation without permanent deletion.
## Scheduled Task
- Add the FilePurger.exe into the Windows Scheduled Tasks Or Modify the Included FilePurger_ScheduledTask.xml File and Import
- Open Task Scheduler (taskschd.msc).
- On the right panel, click Import Task….
- Select your .xml file.
- In the General tab, change the User to your own account (click Change User or Group).
- Adjust StartBoundary date/time in the XML or inside Task Scheduler if you want a different run time.
- Click OK — it will ask for your Windows password (so it can run even when you’re logged off).
and press Enter.

## ⚠️ Safety Notes

- FilePurger never deletes files directly — they are moved to quarantine.
- Review quarantine contents before manual deletion.
- Run with administrative rights to ensure all drives are scanned.

📜 License
MIT License – free to use, modify, and distribute.
## ✍️ Author
Developed by Anjum Sohail – 2025.
