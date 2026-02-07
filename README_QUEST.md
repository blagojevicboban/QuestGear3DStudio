# QuestStream 3D Processor - Dokumentacija

Ovaj alat omogućava 3D rekonstrukciju scena snimljenih pomoću **Meta Quest 3** uređaja (koristeći OpenQuestCapture ili slične alate). Pipeline pretvara sirove slike i depth mape u teksturirani 3D model.

## 🚀 Brzi početak

1. **Učitavanje podataka**:
   - Kliknite na **"Load Folder"** i izaberite raspakovani folder sa Quest podacima.
   - Program će automatski detektovati Quest format i kreirati `frames.json` (ako već ne postoji).
2. **Podešavanja (Settings)**:
   - Kliknite na ikonicu zupčanika (gore desno).
   - **Voxel Size**: Postavite na `0.02` za dobar balans, ili `0.01` za visok kvalitet.
   - **Frame Interval**: Postavite na `1` da procesujete svaki frejm, ili `5` za brzi pregled.
3. **Rekonstrukcija**:
   - Kliknite na **"Start Reconstruction"**.
   - Pratite progres u logovima. Kada se završi, videćete broj generisanih temena (vertices).
4. **Vizuelizacija**:
   - Kliknite na **"Visualizer (External)"** da otvorite 3D pregled.

---

## 🛠️ Tehnički Pipeline

### 1. Preprocesiranje Slikovnih Podataka
- **YUV u RGB**: Quest snima slike u `YUV_420_888` formatu. Naš procesor vrši konverziju u standardni RGB format koristeći OpenCV.
- **Sirova Dubina (Raw Depth)**: Depth mape se učitavaju kao `float32` vrednosti iz `.raw` fajlova. Pošto Quest 3 generiše dubinu u metrima, vršimo skaliranje i čišćenje nevalidnih vrednosti (Infinity/NaN).

### 2. Geometrijska Integracija (TSDF)
Koristimo **Scalable TSDF Volume** (iz Open3D biblioteke) koji funkcioniše na sledeći način:
- Svaki RGB-D frejm se projektuje u 3D prostor koristeći **intrinsics** parametre (focal length, principal point) i **pose** (poziciju i rotaciju headset-a).
- Podaci se akumuliraju u volumetrijsku mrežu (voxels).
- Na kraju se koristi **Marching Cubes** algoritam za ekstrakciju finalnog trouglastog mesha.

---

## 📂 Struktura Podataka (Meta Quest format)

Program očekuje sledeće fajlove u folderu:
- `frames.json`: Glavni indeks sa pozama i putanjama.
- `left_camera_raw/`: Sadrži `.yuv` slike.
- `left_depth/`: Sadrži `.raw` depth mape.
- `left_camera_image_format.json`: Informacije o rezoluciji slika.
- `left_depth_descriptors.csv`: Informacije o rezoluciji i opsegu dubine.

---

## 💡 Saveti za najbolje rezultate

- **Osvetljenje**: Snimajte prostore sa dobrim, difuznim osvetljenjem kako bi YUV slike bile jasne.
- **Brzina kretanja**: Pomerajte se polako dok snimate. Brzi pokreti uzrokuju motion blur koji kvari 3D rekonstrukciju.
- **Preklapanje (Overlap)**: Obezbedite da se frejmovi preklapaju (kružite oko objekata) kako bi TSDF volumen mogao da spoji delove scene.
- **Voxel Size**: Ako imate 0 vertices na kraju, proverite da li je `Voxel Size` previše mali za nivo šuma u depth mapi. `0.02` je obično sigurna vrednost.

## 📦 Zavisnosti
Aplikacija koristi:
- **Flet**: Za moderan korisnički interfejs.
- **Open3D**: Za moćnu 3D obradu i vizuelizaciju.
- **OpenCV & NumPy**: Za brzu obradu piksela i nizova.
