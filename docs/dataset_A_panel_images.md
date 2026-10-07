# Dataset A Audit: Solar Panel Images for Condition & Fault Classification

*Last updated: October 2026*  
*Project: SolarSense EMS (Industrial AI Digital Twin & Data Engineering)*  
*Module: Solar Health & Econometric Cleaning Advisor (Computer Vision Signal)*  
*Owner: Team Member 2*  

---

## 1. Candidate Comparison & Raw Data Audit

| Candidate Name | Direct Link | License | Total Size | Raw Images / Classes | Curated Status | Verified? | Fit Score (1–5) |
| :--- | :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| **PV Panel Defect Dataset** *(alicjalena)* | [Kaggle](https://www.kaggle.com/datasets/alicjalena/pv-panel-defect-dataset) | CC BY-NC-SA 4.0 | 496.4 MB | 1,574 images (6 classes) | 871 unique images; 71.5% test-train leakage in raw splits | **Audited** | 4.8 / 5.0 (after deduplication) |
| **Solar Panel Dust Detection** *(hemanthsai7)* | [Kaggle](https://www.kaggle.com/datasets/hemanthsai7/solar-panel-dust-detection) | CC0 (Public Domain) | 1,212.5 MB (1.27 GB) | 2,562 images (Clean & Dusty only) | 2,331 unique images; 231 duplicates | **Audited** | 3.5 / 5.0 (standalone) |
| **SolarSense Master V1** *(Curated)* | Local: `data/processed/panel_images/solarsense_master_v1` | CC BY-NC-SA 4.0 | ~140 MB | **635 unique images (5 classes)**<br>• Clean: 210<br>• Dusty: 210<br>• Bird-drop: 73<br>• Electrical-damage: 78<br>• Physical-damage: 64 | **100% leak-free, perceptual deduplication, 512×512 Lanczos** | **PASS (Protocol 1)** | **5.0 / 5.0** |

---

## 2. File-by-File Data Engineering & Deduplication Audit

The raw combined pool comprised **4,136 image files**. Our file-by-file audit and two-stage deduplication pipeline ([`src/vision/build_master_dataset.py`](file:///home/bakar/Documents/Solar%20Sens%20EMS/src/vision/build_master_dataset.py)) revealed:

1. **Color Channel Normalization**:
   - Out of 4,136 images, 107 were RGBA (transparency channel), 27 were palette-based (P mode), and 1 was CMYK.
   - All accepted images were safely converted to standard **3-channel RGB** with alpha compositing over a neutral background to prevent PyTorch/Torchvision loader crashes.
2. **Climate Context Pruning**:
   - 262 snow-covered images were removed as Lahore never experiences snow.
3. **Exact Duplication**:
   - **1,026 exact byte duplicates** were removed via SHA256 checksum tracking.
4. **Perceptual Near-Duplication & Cross-Class Conflict Removal**:
   - Using 64-bit difference hashing (`dHash` with Hamming distance $\le 2$), **329 near-duplicate images** were eliminated.
   - *Key finding:* Several identical frames were labeled as "Dusty" in one raw dataset and "Bird-drop" in another. Enforcing global perceptual deduplication completely resolved these label conflicts.
5. **Standardized Geometry**:
   - Every accepted image was resized to **512 × 512 px** using anti-aliasing Lanczos interpolation with aspect-ratio preserving letterbox padding.

---

## 3. Final Master Dataset: `SolarSense Master V1`

Located at: `data/processed/panel_images/solarsense_master_v1/`

### Class Distribution & Protocol 1 Compliance:
| Class | Train (70%) | Val (15%) | Test (15%) | Total Images | Share (%) | Protocol 1 Rule ($\ge$ 10%) | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Clean** | 147 | 31 | 32 | **210** | 33.07% | $\ge$ 10% | **PASS** |
| **Dusty** | 147 | 31 | 32 | **210** | 33.07% | $\ge$ 10% | **PASS** |
| **Electrical Damage** | 54 | 11 | 13 | **78** | 12.28% | $\ge$ 10% | **PASS** |
| **Bird Droppings** | 51 | 10 | 12 | **73** | 11.50% | $\ge$ 10% | **PASS** |
| **Physical Damage** | 44 | 9 | 11 | **64** | 10.08% | $\ge$ 10% | **PASS** |
| **GRAND TOTAL** | **443** | **92** | **100** | **635** | **100.00%** | — | **OPTIMAL** |

### Automated Protocol 1 Verification Results:
- **PIL Image Integrity:** `[PASS]` 100% of images (635/635) opened cleanly.
- **Class Balance:** `[PASS]` All 5 classes satisfy $\ge 10.0\%$ representation.
- **Exact & Near Duplicates:** `[PASS]` 0 duplicate hashes (100% unique panel images).
- **Cross-Split Data Leakage:** `[PASS]` 0 shared images across Train, Val, and Test splits.
- **Resolution Uniformity:** `[PASS]` Exactly 512 × 512 px across 100% of images.
- **Metadata Consistency:** `[PASS]` All 635 images mapped in [`metadata.csv`](file:///home/bakar/Documents/Solar%20Sens%20EMS/data/processed/panel_images/solarsense_master_v1/metadata.csv).
- **Verification Grid:** Saved at [docs/samples/master_dataset_grid.png](file:///home/bakar/Documents/Solar%20Sens%20EMS/docs/samples/master_dataset_grid.png).

---

## 4. Metadata Schema (`metadata.csv`)
Each image in the master dataset has complete lineage tracked:
- `image_id`: Unique identifier (e.g., `clean_train_0001`)
- `class`: Canonical class name
- `split`: `train`, `val`, or `test`
- `filename`: Standardized file name (`clean_train_0001.jpg`)
- `relative_path`: Path within dataset
- `source_dataset`: Original source (`alicjalena` or `hemanthsai7`)
- `original_filename`: Raw file name
- `original_width` & `original_height`: Raw dimensions
- `original_aspect_ratio`: Raw aspect ratio
- `original_mode`: Raw color mode (RGB, RGBA, P, etc.)
- `processed_width` & `processed_height`: `512`
- `mean_brightness` & `contrast_std`: Normalized luminance metrics
- `processed_sha256`: SHA-256 hash of processed file
- `dhash_hex`: 64-bit difference hash
