# Arhitektura Projekta QuestStream

Ovaj dokument opisuje tehnički dizajn i tok podataka unutar aplikacije.

## 1. Pregled Komponenti

Aplikacija je podeljena na UI sloj i logički sloj (backend) koji komuniciraju putem callback funkcija u okviru paralelnih niti (threading).

### UI Sloj (`modules/gui.py`)
- Koristi **Flet** za renderovanje interfejsa.
- Upravlja stanjem aplikacije (putanje do privremenih foldera, učitani meševi).
- Pokreće asinhrone procese u pozadinskim nitima kako bi UI ostao responzivan.
- Sadrži `add_log` funkciju koja centralizuje ispis svih operacija.

### Ingestion Sloj (`modules/ingestion.py`)
- **ZipValidator**: Proverava da li ZIP fajl ima ispravnu strukturu (prisustvo `frames.json` i potrebnih foldera).
- **AsyncExtractor**: Nasleđuje `threading.Thread`. Raspakuje ZIP u privremeni folder sistema (`tempfile`).

### Procesni Sloj (`modules/image_processing.py`)
- Implementira low-level transformacije slika.
- **yuv_to_rgb**: Konverzija iz NV12/NV21 formata (standard za Quest) u RGB koristeći OpenCV.
- **filter_depth**: Primena bilateralnog filtera na depth mape radi smanjenja šuma pre integracije.

### Rekonstrukcioni Sloj (`modules/reconstruction.py`)
- Centralni deo backend-a koji koristi **Open3D**.
- **QuestReconstructor**: Inicijalizuje `ScalableTSDFVolume`.
- **Integracija**: Pretvara numeričke podatke u `RGBDImage` i integriše ih u 3D prostor koristeći matricu poze (pose).

## 2. Tok Podataka (Data Flow)

1. **Korisnik bira ZIP** -> `FilePicker` u GUI-u.
2. **Validacija** -> `ZipValidator` proverava CRC i strukturu.
3. **Ekstrakcija** -> `AsyncExtractor` raspakuje fajlove u `/tmp/quest_stream_XXXX`.
4. **Pokretanje Rekonstrukcije**:
   - `ReconstructionThread` čita `frames.json`.
   - Za svaki frejm:
     - Čita se BIN/YUV fajl -> `yuv_to_rgb`.
     - Čita se Depth fajl -> `filter_depth`.
     - Frame se integriše u `Volume`.
5. **Finalizacija**: `extraxt_mesh()` generiše TriangleMesh objekat koji se šalje nazad u GUI za vizuelizaciju.

## 3. Upravljanje Konfiguracijom

Svi parametri se čuvaju u `config.yml`. `ConfigManager` omogućava:
- Učitavanje podrazumevanih (default) vrednosti ako fajl ne postoji.
- Dinamičko ažuriranje vrednosti putem Settings dijaloga bez restarta aplikacije.

## 4. Error Handling

Aplikacija koristi `try-except` blokove u svim kritičnim nitima. Greške se šalju nazad u GUI putem `on_error` callback-a i ispisuju se CRVENOM bojom u logovima (ili SnackBar obaveštenjima).
