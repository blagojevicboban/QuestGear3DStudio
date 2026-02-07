---
description: Kako pokrenuti, debugeovati i bildovati QuestStream aplikaciju.
---

### 1. Pokretanje (Run)
Za standardno pokretanje aplikacije tokom razvoja koristite:
```powershell
python main.py
```
Ili direktno preko Flet-a (omogućava hot-reload za UI promene):
```powershell
python -m flet run main.py
```

### 2. Debugovanje (Debug)
Aplikacija je konfigurisana za rad sa VS Code debugger-om.
1. Odaberite **"Python: Current File"** u Run and Debug panelu (ili pritisnite `F5`).
2. Postavite breakpoint-ove u `modules/gui.py` ili `modules/reconstruction.py` kako biste pratili tok podataka.
3. Logovi će se pojaviti u terminalu ali i unutar samog log prozora u aplikaciji.

### 3. Bildovanje (Build)
Flet omogućava pretvaranje Python koda u standalone izvršne fajlove (.exe).
// turbo
1. Prvo instalirajte flet build zavisnosti:
   ```powershell
   pip install "flet[all]"
   ```
2. Pokrenite komandu za bildovanje Windows aplikacije:
   ```powershell
   python -m flet build windows
   ```
   *Napomena: Rezultat će biti u `build/windows` folderu.*
3. Za kreiranje jednog .exe fajla (single-file):
   ```powershell
   python -m flet build windows --include-all-files
   ```

### 4. Zavisnosti
Uvek proverite da li su sve biblioteke instalirane:
```powershell
pip install -r requirements.txt
```
