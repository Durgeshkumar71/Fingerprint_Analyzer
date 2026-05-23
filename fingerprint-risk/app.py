from flask import Flask, render_template, request, jsonify
import cv2
import numpy as np
from PIL import Image
import base64
import io
import os
import uuid

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10MB max
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def analyze_fingerprint_risk(image_bytes):
    """
    Analyzes an uploaded image for fingerprint visibility risk.
    Uses computer vision to detect ridge patterns, contrast, and finger regions.
    """
    # Decode image
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None

    original = img.copy()
    h, w = img.shape[:2]

    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # --- STEP 1: Skin detection (find finger regions) ---
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_skin = np.array([0, 20, 70], dtype=np.uint8)
    upper_skin = np.array([20, 255, 255], dtype=np.uint8)
    skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)

    # Also check another range for darker skin
    lower_skin2 = np.array([0, 10, 60], dtype=np.uint8)
    upper_skin2 = np.array([25, 200, 255], dtype=np.uint8)
    skin_mask2 = cv2.inRange(hsv, lower_skin2, upper_skin2)
    skin_mask = cv2.bitwise_or(skin_mask, skin_mask2)

    skin_area_ratio = np.count_nonzero(skin_mask) / (h * w)

    # --- STEP 2: Ridge/texture detection using Gabor filters ---
    def apply_gabor(gray_img):
        responses = []
        for theta in [0, np.pi/4, np.pi/2, 3*np.pi/4]:
            kernel = cv2.getGaborKernel((21, 21), 4.0, theta, 10.0, 0.5, 0, ktype=cv2.CV_32F)
            filtered = cv2.filter2D(gray_img, cv2.CV_8UC3, kernel)
            responses.append(filtered)
        return np.mean(responses, axis=0).astype(np.uint8)

    gabor_response = apply_gabor(gray)
    ridge_intensity = float(np.mean(gabor_response))

    # --- STEP 3: Edge density (sharpness / detail level) ---
    edges = cv2.Canny(gray, 50, 150)
    edge_density = float(np.count_nonzero(edges)) / (h * w)

    # --- STEP 4: Image resolution & clarity score ---
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    clarity_score = min(laplacian_var / 1000.0, 1.0)

    # --- STEP 5: Local contrast in skin regions ---
    if np.count_nonzero(skin_mask) > 100:
        skin_pixels = gray[skin_mask > 0]
        local_contrast = float(np.std(skin_pixels)) / 128.0
    else:
        local_contrast = 0.0

    # --- RISK SCORE CALCULATION ---
    # Weights based on real biometric extraction factors
    w_skin = 0.25       # presence of fingers
    w_ridge = 0.25      # ridge pattern visibility
    w_edge = 0.20       # detail / sharpness
    w_clarity = 0.20    # image quality
    w_contrast = 0.10   # local contrast in finger region

    skin_score = min(skin_area_ratio * 3.0, 1.0)
    ridge_score = min(ridge_intensity / 128.0, 1.0)
    edge_score = min(edge_density * 20.0, 1.0)
    contrast_score = min(local_contrast, 1.0)

    raw_risk = (
        skin_score * w_skin +
        ridge_score * w_ridge +
        edge_score * w_edge +
        clarity_score * w_clarity +
        contrast_score * w_contrast
    )
    risk_percent = int(min(raw_risk * 100 * 1.8, 99))  # scale & cap

    # --- STEP 6: Create highlighted output image ---
    output = original.copy()

    # Highlight detected skin/finger regions
    skin_highlight = np.zeros_like(output)
    skin_highlight[skin_mask > 0] = [0, 50, 255]  # red tint on fingers
    output = cv2.addWeighted(output, 0.7, skin_highlight, 0.3, 0)

    # Overlay ridge visualization
    ridge_overlay = cv2.applyColorMap(gabor_response, cv2.COLORMAP_INFERNO)
    ridge_mask = (gabor_response > 60).astype(np.uint8) * 255
    ridge_colored = np.zeros_like(output)
    ridge_colored[ridge_mask > 0] = ridge_overlay[ridge_mask > 0]
    output = cv2.addWeighted(output, 0.75, ridge_colored, 0.25, 0)

    # Draw edge contours
    contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        if cv2.contourArea(cnt) > 500:
            cv2.drawContours(output, [cnt], -1, (0, 255, 180), 2)

    # Encode output image to base64
    _, buffer = cv2.imencode('.jpg', output, [cv2.IMWRITE_JPEG_QUALITY, 90])
    output_b64 = base64.b64encode(buffer).decode('utf-8')

    # Risk level label
    if risk_percent >= 70:
        level = "CRITICAL"
        color = "#ff2e2e"
    elif risk_percent >= 45:
        level = "HIGH"
        color = "#ff8c00"
    elif risk_percent >= 25:
        level = "MODERATE"
        color = "#f5c518"
    else:
        level = "LOW"
        color = "#00e676"

    return {
        "risk_score": risk_percent,
        "risk_level": level,
        "risk_color": color,
        "skin_detected": round(skin_area_ratio * 100, 1),
        "ridge_visibility": round(ridge_score * 100, 1),
        "image_clarity": round(clarity_score * 100, 1),
        "edge_density": round(edge_score * 100, 1),
        "analyzed_image": output_b64,
        "resolution": f"{w}x{h}px",
        "recommendations": get_recommendations(risk_percent)
    }


def get_recommendations(risk_score):
    recs = []
    if risk_score >= 45:
        recs.append("Curl or fold fingers in photos to hide ridge patterns")
        recs.append("Avoid high-resolution close-up finger shots on social media")
        recs.append("Enable 2FA on accounts — don't rely solely on biometrics")
    if risk_score >= 25:
        recs.append("Use blur/mosaic filter on finger areas before posting")
        recs.append("Keep hands at a distance from camera in selfies")
    recs.append("Review privacy settings on Snapchat & Instagram")
    recs.append("Use strong passwords as backup to biometric locks")
    return recs


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    allowed = {'png', 'jpg', 'jpeg', 'webp', 'bmp'}
    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in allowed:
        return jsonify({"error": "Unsupported file type"}), 400

    image_bytes = file.read()
    result = analyze_fingerprint_risk(image_bytes)

    if result is None:
        return jsonify({"error": "Could not process image"}), 500

    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
