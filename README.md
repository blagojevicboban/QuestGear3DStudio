# QuestStream 3D Processor

QuestStream je moćan Python alat za rekonstrukciju 3D modela iz podataka snimljenih putem **Meta Quest 3** headseta. Aplikacija procesira RGB slike, depth mape i podatke o poziciji kamere kako bi generisala visokokvalitetne 3D meševe koristeći TSDF (Truncated Signed Distance Function) integraciju.

## Glavne Funkcionalnosti

-   **Moderan UI**: Korisnički interfejs izgrađen pomoću **Flet** (Flutter for Python) sa tamnom temom.
-   **Validacija Podataka**: Automatska provera integriteta ZIP fajlova pre ekstrakcije.
-   **Prošireni Logovi**: Detaljan ispis svih procesa (raspakivanje, procesiranje frejmova, ekstrakcija modela) sa vremenskim markerima.
-   **3D Rekonstrukcija**: Optimizovana integracija frejmova koristeći ScalableTSDFVolume.
-   **Vizuelizacija**: Integrisani Open3D pregledač za inspekciju generisanog modela.
-   **Konfiguracija**: Lako podešavanje parametara (voxel size, max depth) direktno u aplikaciji.

## Preduslovi

-   Windows 10/11
-   Python 3.10 ili 3.11 (Preporučeno zbog podrške za `open3d`)
-   Meta Quest 3 podaci u ZIP formatu

## Instalacija

1.  **Klonirajte repozitorijum:**
    ```bash
    git clone https://github.com/yourusername/QuestStream.git
    cd QuestStream
    ```

2.  **Kreirajte virtuelno okruženje:**
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Instalirajte zavisnosti:**
    ```bash
    pip install -r requirements.txt
    ```

## Upotreba

1.  **Pokretanje aplikacija:**
    ```bash
    python main.py
    ```

2.  **Učitavanje podataka:**
    -   Kliknite na dugme **Load ZIP**.
    -   Aplikacija će automatski otvoriti `D:\METAQUEST` ukoliko on postoji.
    -   ZIP mora sadržati:
        -   `frames.json`: Meta podaci (intrinsics, pose, timestamps).
        -   `raw_images/`: Folder sa BIN/YUV slikama.
        -   `depth_maps/`: Folder sa dubinskim mapama.

3.  **Procesiranje:**
    -   Nakon ekstrakcije, kliknite **Start Reconstruction**.
    -   Pratite napredak preko progres bara i detaljnih logova na dnu ekrana.

4.  **Pregled:**
    -   Po završetku, kliknite **Visualizer (External)** da otvorite interaktivni 3D prikaz.

## Projektna Struktura

-   `main.py`: Ulazna tačka aplikacije.
-   `modules/`:
    -   `gui.py`: Frontend logika (Flet) i upravljanje procesnim nitima.
    -   `reconstruction.py`: Implementacija TSDF rekonstrukcije.
    -   `ingestion.py`: Validacija i asinhrono raspakivanje podataka.
    -   `image_processing.py`: Obrada slike (YUV -> RGB) i filtriranje dubine.
    -   `config_manager.py`: Upravljanje podešavanjima putem YAML fajla.
-   `.agent/workflows/app-guide.md`: Detaljan vodič za razvoj i bildovanje.

## Razvoj i Debugging

Za detaljne instrukcije o tome kako se aplikacija debugeuje i bilduje u izvršni fajl, pogledajte:
`/.agent/workflows/app-guide.md`

## Licenca

[MIT License](LICENSE)
