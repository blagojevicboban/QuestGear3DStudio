---
description: How to run, debug and build the QuestStream application.
---

### 1. Run
For standard application startup during development, use:
```powershell
python main.py
```
Or directly via Flet (allows hot-reload for UI changes):
```powershell
python -m flet run main.py
```

### 2. Debugging
The application is configured to work with the VS Code debugger.
1. Select **"Python: Current File"** in the Run and Debug panel (or press `F5`).
2. Set breakpoints in `modules/gui.py` or `modules/reconstruction.py` to trace the data flow.
3. Logs will appear in the terminal but also within the log window inside the application itself.

### 3. Building
Flet allows converting Python code into standalone executable files (.exe).
// turbo
1. First, install flet build dependencies:
   ```powershell
   pip install "flet[all]"
   ```
2. Run the command to build the Windows application:
   ```powershell
   python -m flet build windows
   ```
   *Note: The result will be in the `build/windows` folder.*
3. To create a single-file executable:
   ```powershell
   python -m flet build windows --include-all-files
   ```

### 4. Dependencies
Always check if all libraries are installed:
```powershell
pip install -r requirements.txt
```
