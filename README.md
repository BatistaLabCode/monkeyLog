# 🐒 MonkeyLog — Data Entry GUI

A PyQt6 desktop app for inserting records into the `monkeyLog` MySQL/MariaDB table.

## Setup

```bash
git clone https://github.com/your-username/monkeylog-gui.git
cd monkeylog-gui
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install PyQt6 pymysql
```

Update the `DB_CONFIG` defaults at the top of `monkey_log_gui.py` with your host, database name, and credentials. These can also be changed at runtime in the app.

## Run

```bash
python monkey_log_gui.py
```

## Build Executable

**Windows:**
```powershell
pip install pyinstaller
pyinstaller --onefile --windowed --name "MonkeyLog" monkey_log_gui.py
# Output: dist\MonkeyLog.exe
```

**Linux:**
```bash
pip install pyinstaller
pyinstaller --onefile --name "MonkeyLog" monkey_log_gui.py
# Output: dist/MonkeyLog
chmod +x dist/MonkeyLog
```

> Binaries are platform-specific — build on the OS you intend to deploy on.

## Notes

- Connection settings are saved per username after a successful Test Connection or Submit
- "Remember Password" stores a base64-obfuscated password — not strong encryption
- Uses PyMySQL instead of `mysql-connector-python` to avoid silent crashes in compiled executables on Windows
