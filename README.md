| Stage | Description |
|-------|-------------|
| 1️⃣ Photo Posted | Victim shares selfie with fingers visible on social media |
| 2️⃣ Ridge Extraction | Attacker applies Gabor filters to extract ridge patterns |
| 3️⃣ Clone Created | Fake fingerprint printed on conductive film or gelatin |
| 4️⃣ Bypass Attempted | Clone used to unlock device or bypass biometric auth |

**Real-world proof:** In 2014, Germany's CCC hacked a Defense Minister's fingerprint from a press conference photo. In 2017, Japanese researchers extracted prints from **3 meters away**.

---

## ✨ Features

- 🖐️ **Skin & Finger Region Detection** — HSV-based multi-range skin detection
- 🌀 **Gabor Filter Ridge Analysis** — 4-orientation fingerprint ridge extraction
- 📊 **Multi-Factor Risk Scoring** — Weighted combination of 5 CV metrics
- 🎨 **Visual Overlay Output** — Highlighted finger regions + ridge heatmap
- 🛡️ **Defense Recommendations** — Personalized tips based on risk level
- ⚡ **Fast & Lightweight** — No ML models, pure OpenCV pipeline

---

## 🛠️ Technologies Used

| Technology | Purpose |
|------------|---------|
| Python 3.8+ | Backend Development |
| Flask | Web Framework |
| OpenCV | Gabor Filters, Skin Detection, Edge Analysis |
| NumPy | Matrix operations & scoring |
| Pillow | Image format handling |
| HTML5/CSS3/JS | Frontend Interface |

---

## 📂 Project Structure
BioCypher/
│
├── app.py                        # Flask backend + CV analysis engine
├── README.md                     # This file
├── BioCypher_Project_Report.docx # Full academic project report
│
└── templates/
└── index.html                # Frontend UI
---

## ⚙️ Installation & Setup

### 1. Clone the Repository
```bash
git clone 
cd BioCypher
```https://github.com/Durgeshkumar71/Fingerprint_Analyzer

### 2. Install Dependencies
```bash
pip install flask opencv-python-headless numpy pillow
```

### 3. Run the App
```bash
python app.py
```

### 4. Open in Browser
http://localhost:5000

---

## 📊 Risk Score Breakdown

| Factor | Weight | What It Measures |
|--------|--------|-----------------|
| Skin Region Detection | 25% | Presence of fingers in frame |
| Ridge Visibility (Gabor) | 25% | Core fingerprint ridge patterns |
| Image Clarity (Laplacian) | 20% | Sharpness = extractability |
| Edge Detail Density | 20% | Structural information level |
| Local Contrast | 10% | Ridge differentiation quality |

| Score | Risk Level |
|-------|-----------|
| 0 – 24 | 🟢 LOW |
| 25 – 44 | 🟡 MODERATE |
| 45 – 69 | 🟠 HIGH |
| 70 – 99 | 🔴 CRITICAL |

---

## 🛡️ Defense Strategies

**Photo Hygiene:**
- Curl or fold fingers in photos to hide ridge patterns
- Avoid high-resolution close-up hand shots on social media
- Apply blur/mosaic filter on fingertips before posting

**Device Security:**
- Use PIN/password as primary lock — not just fingerprint
- Enable 2FA on all critical accounts
- Avoid biometric-only auth for banking apps

---

## 📚 References

1. Starbug (CCC) — "Fingerprinting without Consent", 31C3, 2014
2. Isao Echizen (NII Japan) — Fingerprint extraction from distance, 2017
3. NIST SP 800-76-2 — Biometric Specifications for Personal Identity Verification
4. OpenCV Docs — Gabor Filter & Feature Detection

---

## 👨‍💻 Author

**Durgesh Kumar**
BSc Cybersecurity — Mehran University of Engineering & Technology (MUET), Jamshoro

---

> *Built for cybersecurity awareness. Use responsibly.*
