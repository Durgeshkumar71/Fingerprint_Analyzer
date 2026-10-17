<div align="center">

# 🛡️ BioCypher 2.0
### *Biometric Cyber Forensics & Photo Privacy Shield*

**A real-time cybersecurity awareness engine that demonstrates how fingerprint ridge patterns can be extracted from social media photos — and empowers users with 1-click active privacy sanitization.**

[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask 3.0](https://img.shields.io/badge/Flask-Backend-000000.svg?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-Computer_Vision-5C3EE8.svg?style=for-the-badge&logo=opencv&logoColor=white)](https://opencv.org/)
[![Security Hardened](https://img.shields.io/badge/Security-OWASP_Top_10_Hardened-10B981.svg?style=for-the-badge&logo=shield&logoColor=white)](#-security-hardening--owasp-compliance)
[![Forensic Standard](https://img.shields.io/badge/Forensics-NIST_SP_800--76--2-38BDF8.svg?style=for-the-badge&logo=target&logoColor=white)](#-forensic--mathematical-foundations)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

[Live Demo](#-quickstart-guide) • [Key Features](#-key-features) • [How It Works](#-how-the-attack-works) • [Forensic Science](#-forensic--mathematical-foundations) • [Security](#-security-hardening--owasp-compliance) • [Academic Credits](#-author--academic-credits)

---

</div>

## 📌 Executive Overview

Every day, millions of selfies and posed photos with visible hands (e.g., **peace signs**, **thumbs up**, **waving**) are posted on Instagram, Snapchat, and TikTok. 

Advancements in high-megapixel smartphone lenses and directional computer vision filters allow adversaries to zoom in, isolate friction ridges, extract forensic minutiae, and construct physical conductive clones (using conductive ink, gelatin, or silicone molds) capable of bypassing biometric capacitive sensors like **Apple TouchID** and **Android Fingerprint Scanners**.

Unlike passwords, **your fingerprints cannot be reset once compromised**. 

**BioCypher** is a dual-purpose platform:
1. **Threat Assessment**: Scans photos to calculate biometric cloning viability against official **FBI / NIST SP 800-76-2** forensic admissibility thresholds.
2. **Active Privacy Defense**: Provides an immediate **1-Click Privacy Shield** that naturally blurs finger ridges while preserving the visual aesthetic of the photo for social media sharing.

---

## ✨ Key Features

| Capability | Technical Implementation | Practical Benefit |
|---|---|---|
| 🔬 **Zero-DC Directional Gabor Filter Bank** | Multi-orientation bandpass kernels ($0^\circ, 30^\circ, 60^\circ, 90^\circ, 120^\circ, 150^\circ$) | Isolates periodic epidermal friction ridges while rejecting false positives from uniform skin. |
| 🧬 **AFIS Minutiae Keypoint Extraction** | Morphological skeleton thinning & neighborhood convolution | Maps candidate ridge terminations (cyan) and bifurcations (magenta) against the legal 12-point threshold. |
| 🛡️ **1-Click Active Privacy Redactor** | Adaptive Gaussian blur, cyber pixel mosaic, adversarial noise | Eradicates ridge extractability; drops risk score below 15% and provides instant safe image download. |
| 👁️ **Interactive Multi-Layer Inspector** | Real-time layer compositor | Toggle between Composite Overview, Ridge Heatmap (Inferno), Minutiae Skeleton, Skin Mask, and Original Photo. |
| 📷 **Live WebRTC Camera Viewfinder** | HTML5 `getUserMedia` camera feed with targeting reticle | Real-time snapshot diagnostics directly within your web browser. |
| ⚡ **Pre-Loaded Benchmark Scenarios** | 4 synthesized forensic test cases | Test peace signs, macro fingertips, curled fists, and distant poses without personal photos. |
| 📄 **Forensic Biometric Audit Dossier** | Dynamic metadata generator & print CSS | Generates clean, executive-ready PDF/print audit reports detailing clone feasibility. |
| 🔒 **Enterprise-Grade Security Hardening** | In-memory sliding-window rate limiter, CSP, magic bytes | Immunized against XSS, decompression bombs, compute flooding (DoS), and directory traversal. |

---

## 🚀 The 3-Step Guided Workflow

```
┌───────────────────────────┐      ┌───────────────────────────┐      ┌───────────────────────────┐
│  STEP 1: SELECT PHOTO     │ ───► │  STEP 2: BIOMETRIC SCAN   │ ───► │  STEP 3: 1-CLICK SHIELD   │
│  Upload, Camera, or Test  │      │  Gabor Filters + Minutiae │      │  Blur Ridges & Download   │
│  Benchmark Scenarios      │      │  Plain-English Verdict    │      │  Safe Photo to Share!     │
└───────────────────────────┘      └───────────────────────────┘      └───────────────────────────┘
```

1. **Step 1: Select Your Photo** — Upload an image, snap a live photo with your webcam, or select a built-in benchmark test case.
2. **Step 2: Biometric Risk Verdict** — The computer vision engine evaluates friction ridge clarity, skin ratio, Laplacian sharpness, and minutiae points, displaying a clear plain-English verdict (Safe, Moderate, High, or Critical).
3. **Step 3: 1-Click Privacy Shield** — Apply a gentle, natural blur to your fingertips that preserves the overall look of your selfie while rendering fingerprint extraction impossible!

---

## 🔍 How the Attack Works

```
Social Media Selfie ──► Zero-DC Gabor Extraction ──► Minutiae Topology ──► Conductive Ink/Mold ──► Biometric Bypass
(Fingers Exposed)       (Friction Ridges Isolated)   (Points Mapped)       (Fake Finger Created)   (Phone Unlocked)
```

1. **Victim Shares Selfie** — A high-resolution photo with fingers pointed towards the lens (such as a V-sign peace pose) is posted publicly.
2. **Ridge Extraction** — Attacker crops the fingertips and applies directional Zero-DC Gabor filters tuned to human friction ridge frequencies (8–12px wavelength).
3. **Minutiae Extraction** — Morphological thinning extracts ridge endings and bifurcations. If $\ge 12$ reliable points are resolved, it satisfies court standards for positive identity match.
4. **Physical Clone Fabrication** — The extracted ridge map is printed onto conductive graphite ink paper or cast in a gelatin/silicone mold.
5. **Sensor Bypass** — The synthetic finger is presented to capacitive sensors (TouchID, Android Fingerprint), granting unauthorized device or account access.

### 🌐 Documented Real-World Incidents

- **German Defense Minister Hack (Chaos Computer Club, 2014)**: Security researcher Jan Krissler (*Starbug*) cloned German Defense Minister Ursula von der Leyen's fingerprint using only high-resolution commercial press photos taken at a public briefing.
- **National Institute of Informatics Study (Japan, 2017)**: Professor Isao Echizen demonstrated successful fingerprint extraction from photos taken up to **3 meters away** under standard indoor ambient lighting.

---

## 📊 Forensic & Mathematical Foundations

### Multiplicative Extractability Risk Index

Biometric vulnerability requires **both** friction ridge visibility and sufficient image quality. BioCypher evaluates risk as the product of **Extractability** and **Environmental Exposure**:

$$\text{Extractability} = R_{\text{gabor}} \times (0.50 + 0.50 \times M_{\text{minutiae}})$$

$$\text{Exposure} = 0.45 \cdot S_{\text{skin}} + 0.35 \cdot C_{\text{clarity}} + 0.15 \cdot E_{\text{edge}} + 0.05 \cdot K_{\text{contrast}}$$

$$\text{Risk Score} = \min(100 \times \text{Extractability} \times \text{Exposure} \times 1.35, 99)$$

### Forensic Risk Tiers

| Score Range | Risk Level | Status | Forensic Threat Interpretation |
|:---:|:---:|:---:|---|
| **0 – 24** | 🟢 **LOW** | SAFE PHOTO | No extractable ridges; fingers curled, hidden, or too distant to clone. |
| **25 – 44** | 🟡 **MODERATE** | PARTIAL EXPOSURE | Fingers present but optical resolution or blur prevents full minutiae mapping. |
| **45 – 69** | 🟠 **HIGH** | VIABLE CLONING RISK | Clear ridge flow; attackers can extract partial AFIS templates. |
| **70 – 99** | 🔴 **CRITICAL** | EXTREME EXPOSURE | Exceeds NIST $\ge 12$ minutiae threshold; physical conductive cloning is viable. |

---

## 🔒 Security Hardening & OWASP Compliance

BioCypher incorporates enterprise defense-in-depth protections:

- 🛡️ **XSS Immunity**: Strict HTML entity escaping (`escapeHtml()`), dynamic `textContent` node rendering, and color whitelisting; blocks DOM-based script injection.
- 🔐 **Administrative RBAC & Salted Hashing**: Role-Based Access Control (`admin` vs `anonymous_user`), PBKDF2-HMAC-SHA256 password hashing with 600,000 rounds and unique salts, and session fixation prevention.
- 📦 **Decompression Bomb Protection**: Magic-byte verification (JPEG, PNG, WEBP, BMP) rejects malicious non-image payloads; auto-downscales images larger than 1920px to prevent memory exhaustion DoS.
- ⏱️ **Multi-Tier Sliding-Window Rate Limiter**: Quotas enforced per IP (Global: 60/min, Forensic CV: 15/min, Auth: 5 attempts/5min lockout), returning RFC 6585 `HTTP 429 Too Many Requests` with `Retry-After` headers.
- 🚫 **Path Traversal Defense**: Canonical path validation prevents directory escape outside designated sample directories.
- 🌐 **OWASP Security Headers**: Injects `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `HSTS (max-age=31536000)`, `Cross-Origin-Opener-Policy: same-origin`, and `Referrer-Policy: strict-origin-when-cross-origin`.
- 🔑 **Zero-Secret Architecture**: All API keys, hashes, and session secrets are managed strictly through environment variables (`.env.example` template provided; `.env` excluded from version control).
- 🛑 **Safe Production Defaults**: Debug consoles are disabled by default (`FLASK_DEBUG=False`), exception stack traces are sanitized, and the server binds securely to `127.0.0.1`.
- 📋 **Security Audit Trail**: Thread-safe in-memory circular audit buffer logging all authentication events, rate limit breaches, and security anomalies without capturing PII.

---

## ⚙️ Quickstart Guide

### Prerequisites
- Python 3.8 or higher
- Modern web browser (Chrome, Edge, Firefox, Brave)

### 1. Clone the Repository
```bash
git clone https://github.com/Durgeshkumar71/Fingerprint_Analyzer.git
cd Fingerprint_Analyzer
```

### 2. Install Required Dependencies
```bash
pip install flask opencv-python-headless numpy pillow
```

### 3. Launch the Application
```bash
python fingerprint-risk/app.py
```
*(Or `python app.py` if running from inside the `fingerprint-risk` directory)*

### 4. Access the Interface
Open your web browser and navigate to:
```
http://localhost:5000
```

---

## 📂 Repository Structure

```
Fingerprint_Analyzer/
│
├── README.md                              # Primary GitHub Documentation
│
└── fingerprint-risk/                      # Core Web Application Package
    ├── app.py                             # Hardened Flask REST server & routing
    ├── cv_engine.py                       # High-precision Computer Vision Forensics engine
    ├── BioCypher_Project_Report.docx      # Full academic research thesis (MUET Jamshoro)
    ├── README.md                          # Package-level documentation
    │
    ├── static/
    │   ├── css/
    │   │   └── style.css                  # Cool Slate & Sky Blue modern design system
    │   ├── js/
    │   │   └── app.js                     # Frontend interactive logic & WebRTC
    │   └── samples/                       # Pre-loaded benchmark scenario images
    │       ├── macro_fingertip.jpg        # Extreme exposure benchmark
    │       ├── peace_sign_selfie.jpg      # Common social selfie benchmark
    │       ├── safe_curled_fist.jpg       # Recommended safe posing benchmark
    │       └── distant_waving_pose.jpg    # Safe distance benchmark
    │
    └── templates/
        └── index.html                     # Clean, accessible single-page layout
```

---

## 📸 Benchmark Test Suite

BioCypher includes 4 pre-loaded benchmark scenarios so evaluators can test immediately:

| Benchmark Case | File | Expected Risk | Forensic Finding |
|---|---|:---:|---|
| ✌️ **Peace Sign Selfie** | `peace_sign_selfie.jpg` | **HIGH (60–75%)** | Index & middle fingertips pointed directly at lens; clear ridge flow. |
| 🔍 **Macro Fingertip** | `macro_fingertip.jpg` | **CRITICAL (90–99%)** | Extreme ridge resolution; exceeds 180 candidate minutiae points. |
| ✊ **Curled Fist Pose** | `safe_curled_fist.jpg` | **LOW (<25%)** | Fingers curled inward; ridges fully shielded from camera view. |
| 🏃 **Distant Waving Pose** | `distant_waving_pose.jpg` | **LOW (<15%)** | Optical resolution too low to resolve sub-millimeter ridge valleys. |

---

## 👨‍💻 Author & Academic Credits

**Durgesh Kumar**  
*BSc Cybersecurity*  
Department of Cyber Security  
**Mehran University of Engineering & Technology (MUET), Jamshoro, Sindh, Pakistan**

*Project developed as part of undergraduate cybersecurity coursework investigating biometric exposure in digital media.*

---

## ⚖️ Ethical Disclaimer

This application is developed **strictly for educational, research, and cybersecurity awareness purposes**. BioCypher does not store, log, or transmit biometric data to third-party servers. All processing executes locally in-memory and image buffers are discarded immediately after analysis.

---

<div align="center">
  <sub>Built with Python, Flask & OpenCV • BioCypher Biometric Privacy Shield • MUET Jamshoro</sub>
</div>
