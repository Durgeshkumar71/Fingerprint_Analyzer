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
