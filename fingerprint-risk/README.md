# BioCypher — Fingerprint Risk Analyzer

> **A cybersecurity awareness tool that demonstrates how fingerprint data can be extracted from social media photos.**

---

## Project Overview

This project demonstrates a real-world biometric security threat: **fingerprint extraction from social media photos**. People frequently post selfies on Snapchat, Instagram, and TikTok with their fingers visible — unknowingly exposing their unique ridge patterns to potential attackers.

**BioCypher** is a Flask-based web application that:
- Analyzes uploaded images for fingerprint exposure risk
- Visualizes detected finger regions and ridge patterns using computer vision
- Calculates a risk score based on multiple biometric factors
- Provides actionable defense recommendations

---

## The Real Threat

In 2014, researchers at Germany's Chaos Computer Club (CCC) successfully cloned German Defense Minister Ursula von der Leyen's fingerprint using **only a photograph taken at a press conference**. In 2017, Japanese researchers demonstrated fingerprint extraction from photos taken from **3 meters away** under standard lighting.

### Attack Flow

```
Social Media Post → CV Ridge Extraction → Fingerprint Clone → Biometric Bypass
```

1. **Photo Posted** — Victim shares selfie with fingers visible
2. **Ridge Extraction** — Attacker applies Gabor filters to extract ridge patterns
3. **Clone Created** — Fake fingerprint printed on conductive film or gelatin
4. **Bypass Attempted** — Clone used to unlock device or app

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3.x + Flask |
| Computer Vision | OpenCV (Gabor filters, Canny edge, HSV skin detection) |
| Image Processing | NumPy, Pillow |
| Frontend | HTML5 + CSS3 + Vanilla JS |
| Visualization | OpenCV color maps + contour drawing |

---

## Installation & Setup

### Prerequisites
- Python 3.8+
- pip

### Step 1 — Clone / Download
```bash
cd fingerprint-risk
```

### Step 2 — Install Dependencies
```bash
pip install flask opencv-python-headless numpy pillow
```

### Step 3 — Run the App
```bash
python app.py
```

### Step 4 — Open in Browser
```
http://localhost:5000
```

---

## How the Analysis Works

### Skin Detection
Using HSV color space thresholding to identify skin/finger regions in the image. The ratio of detected skin area to total image area is a key risk factor.

### Gabor Filter Ridge Detection
Gabor filters are directional frequency filters commonly used in fingerprint recognition systems. By applying them at multiple orientations (0°, 45°, 90°, 135°), ridge patterns in finger regions are amplified.

```python
kernel = cv2.getGaborKernel((21, 21), 4.0, theta, 10.0, 0.5, 0, ktype=cv2.CV_32F)
filtered = cv2.filter2D(gray_img, cv2.CV_8UC3, kernel)
```

### Image Clarity Score
Using Laplacian variance to measure sharpness — a clearer image means more extractable detail.

### Risk Score Formula
```
Risk = (Skin Score × 0.25) + (Ridge Score × 0.25) + 
       (Edge Score × 0.20) + (Clarity Score × 0.20) + 
       (Contrast Score × 0.10)
```

| Score | Risk Level |
|-------|-----------|
| 0–24 | LOW |
| 25–44 | MODERATE |
| 45–69 | HIGH |
| 70–99 | CRITICAL |

---

## Defense Strategies

### Photo Hygiene
- Curl or fold fingers in photos
- Keep hands away from camera lens
- Apply blur/mosaic filter to fingertips before posting
- Avoid high-resolution close-up hand shots

### Device Security
- Use PIN/password as primary authentication (not just fingerprint)
- Enable liveness detection on supported devices
- Use 2FA on all critical accounts
- Avoid biometric-only authentication for banking apps

### Awareness
- Review and restrict social media privacy settings
- Educate friends and family about biometric exposure
- Monitor accounts for unauthorized access attempts

---

## Project Structure

```
fingerprint-risk/
├── app.py                  # Flask backend + CV analysis logic
├── templates/
│   └── index.html          # Frontend UI (single-page app)
├── static/
│   └── uploads/            # Temporary upload directory
└── README.md               # This file
```

---

## Ethical Disclaimer

This tool is built **strictly for cybersecurity education and awareness**. No fingerprint data is stored, logged, or transmitted. All image processing happens in-memory and uploaded images are discarded immediately after analysis.

This project was developed as part of cybersecurity coursework at **Mehran University of Engineering & Technology (MUET), Jamshoro**.

---

## References

1. Starbug (CCC), "Fingerprinting without Consent" — Chaos Communication Congress, 2014
2. Isao Echizen, NII Japan — "Fingerprint extraction from photos", 2017
3. NIST Biometric Standards — SP 800-76-2
4. OpenCV Documentation — Gabor Filter Implementation

---

*Built with Python + Flask + OpenCV | BioCypher Fingerprint Risk Analyzer*
