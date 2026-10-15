"""
BioCypher 2.0 — Biometric Cybersecurity & Fingerprint Exposure Suite
===================================================================
Hardened Flask Backend Server providing:
- High-performance multi-spectral biometric CV forensics (/analyze)
- Active defense privacy redactor & ridge sanitizer (/sanitize)
- Preset sample scenario gallery (/api/samples)
- Comprehensive OWASP Top 10 defense & security hardening
"""

from flask import Flask, render_template, request, jsonify, make_response
from werkzeug.utils import secure_filename
import os
import base64
import time
import collections
import threading
import cv_engine

app = Flask(__name__)

# Enforce strict 16MB upload limit
MAX_FILE_MB = 16
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_MB * 1024 * 1024

UPLOAD_FOLDER = os.path.join('static', 'uploads')
SAMPLES_FOLDER = os.path.join('static', 'samples')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SAMPLES_FOLDER, exist_ok=True)

# ---------------------------------------------------------------------------
# Rate Limiting & Abuse Prevention Middleware
# ---------------------------------------------------------------------------
RATE_LIMIT_WINDOW = 60  # seconds
MAX_REQUESTS_PER_WINDOW = 40  # requests per window per IP
_ip_request_history = collections.defaultdict(list)
_rate_limit_lock = threading.Lock()

def is_client_rate_limited(client_ip):
    """
    Sliding window rate limiter to prevent computational DoS on CPU-heavy CV endpoints.
    """
    now = time.time()
    with _rate_limit_lock:
        timestamps = _ip_request_history[client_ip]
        # Prune older than window
        valid_timestamps = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
        _ip_request_history[client_ip] = valid_timestamps
        if len(valid_timestamps) >= MAX_REQUESTS_PER_WINDOW:
            return True
        _ip_request_history[client_ip].append(now)
        return False

# ---------------------------------------------------------------------------
# HTTP Security Headers (OWASP Top 10 Compliance)
# ---------------------------------------------------------------------------
@app.after_request
def apply_security_headers(response):
    """
    Attaches defense-in-depth security headers to every response.
    """
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(self), microphone=(), geolocation=()'
    
    # Content-Security-Policy (CSP) restricting execution boundaries
    csp = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        "media-src 'self' blob:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self';"
    )
    response.headers['Content-Security-Policy'] = csp
    return response

# ---------------------------------------------------------------------------
# Benchmark Sample Scenarios
# ---------------------------------------------------------------------------
SAMPLE_SCENARIOS = [
    {
        "id": "peace_sign",
        "title": "Peace Sign / V-Pose Selfie",
        "filename": "peace_sign_selfie.jpg",
        "category": "Social Media Selfie",
        "risk_expectation": "CRITICAL / HIGH",
        "tag": "Common Snapchat Pose",
        "description": "Standard selfie pose with two fingers pointed directly at lens; exposes index and middle finger ridges."
    },
    {
        "id": "macro_finger",
        "title": "Macro Fingertip Close-Up",
        "filename": "macro_fingertip.jpg",
        "category": "High-Res Macro",
        "risk_expectation": "CRITICAL (90-99%)",
        "tag": "Maximum Forensic Threat",
        "description": "Close-up macro image exposing complete friction ridge flow, core pattern, and forensic minutiae."
    },
    {
        "id": "safe_fist",
        "title": "Curled Fingers / Closed Fist",
        "filename": "safe_curled_fist.jpg",
        "category": "Recommended Pose",
        "risk_expectation": "LOW / SAFE (<25%)",
        "tag": "Defense Strategy",
        "description": "Hand positioned with fingers curled inwards; friction ridges are completely obscured from camera view."
    },
    {
        "id": "distant_waving",
        "title": "Distant Waving Pose",
        "filename": "distant_waving_pose.jpg",
        "category": "Distance Photo",
        "risk_expectation": "LOW (<15%)",
        "tag": "Low Optical Resolution",
        "description": "Hand is visible at a distance; optical resolution is too low for ridge pattern reconstruction."
    }
]

def sanitize_output_filename(filename, max_length=48):
    """Safely sanitizes and bounds filename string for XSS and log integrity."""
    if not filename:
        return "uploaded_image.jpg"
    safe = secure_filename(str(filename))
    if not safe:
        safe = "image.jpg"
    return safe[:max_length]

def extract_image_bytes(req):
    """
    Extracts image bytes from multipart form-data or JSON with strict path traversal & size validation.
    """
    # 1. Check for file in multipart form-data
    if 'image' in req.files:
        file = req.files['image']
        if file and file.filename != '':
            raw_fname = sanitize_output_filename(file.filename)
            raw_bytes = file.read()
            return raw_bytes, raw_fname

    # 2. Check for JSON payload with base64 image data
    if req.is_json:
        data = req.get_json(silent=True)
        if data and isinstance(data, dict):
            b64_str = data.get('image_b64')
            if b64_str and isinstance(b64_str, str):
                if ',' in b64_str:
                    b64_str = b64_str.split(',', 1)[1]
                try:
                    raw_bytes = base64.b64decode(b64_str, validate=True)
                    return raw_bytes, "webcam_capture.jpg"
                except Exception:
                    return None, None

    # 3. Check for sample_id with path traversal defense
    sample_id = None
    if req.form:
        sample_id = req.form.get('sample_id')
    if not sample_id and req.is_json:
        json_data = req.get_json(silent=True)
        if json_data and isinstance(json_data, dict):
            sample_id = json_data.get('sample_id')

    if sample_id and isinstance(sample_id, str):
        for s in SAMPLE_SCENARIOS:
            if s['id'] == sample_id:
                safe_fname = os.path.basename(s['filename'])
                sample_path = os.path.abspath(os.path.join(SAMPLES_FOLDER, safe_fname))
                samples_dir_abs = os.path.abspath(SAMPLES_FOLDER)
                # Ensure path is strictly within samples folder
                if sample_path.startswith(samples_dir_abs) and os.path.isfile(sample_path):
                    with open(sample_path, 'rb') as f:
                        return f.read(), safe_fname

    return None, None

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    return render_template('index.html', samples=SAMPLE_SCENARIOS)

@app.route('/api/samples', methods=['GET'])
def get_samples():
    """Returns metadata for the pre-loaded sample scenario test suite."""
    return jsonify({
        "status": "success",
        "samples": SAMPLE_SCENARIOS
    })

@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Full biometric exposure & minutiae diagnostic endpoint.
    Protected by sliding-window rate limiting, magic byte verification, and decompression bomb defenses.
    """
    client_ip = request.remote_addr or 'unknown'
    if is_client_rate_limited(client_ip):
        return jsonify({
            "error": "Rate limit exceeded. Too many forensic scans requested.",
            "retry_after_seconds": 30
        }), 429

    image_bytes, filename = extract_image_bytes(request)
    if not image_bytes:
        return jsonify({
            "error": "No valid image provided. Please upload an image file, capture via webcam, or choose a benchmark preset."
        }), 400

    results = cv_engine.analyze_image_forensics(image_bytes)
    if results is None:
        return jsonify({
            "error": "Image validation failed. The payload is either corrupt, unreadable, or not a supported image format (JPEG, PNG, WEBP, BMP)."
        }), 422

    results["filename"] = sanitize_output_filename(filename)
    return jsonify(results)

@app.route('/sanitize', methods=['POST'])
def sanitize():
    """
    Active Defense Endpoint:
    Sanitizes detected finger/hand regions with adaptive blur, cyber mosaic, or adversarial scramble.
    """
    client_ip = request.remote_addr or 'unknown'
    if is_client_rate_limited(client_ip):
        return jsonify({
            "error": "Rate limit exceeded. Please wait before submitting additional sanitization requests.",
            "retry_after_seconds": 30
        }), 429

    image_bytes, filename = extract_image_bytes(request)
    if not image_bytes:
        return jsonify({"error": "No image payload provided for sanitization."}), 400

    # Sanitize and bound mode parameter
    raw_mode = 'blur'
    if request.form and 'mode' in request.form:
        raw_mode = str(request.form.get('mode', 'blur')).strip().lower()
    elif request.is_json:
        data = request.get_json(silent=True) or {}
        raw_mode = str(data.get('mode', 'blur')).strip().lower()

    valid_modes = ('blur', 'mosaic', 'scramble')
    mode = raw_mode if raw_mode in valid_modes else 'blur'

    # Sanitize intensity parameter
    intensity = 7
    raw_intensity = None
    if request.form and 'intensity' in request.form:
        raw_intensity = request.form.get('intensity')
    elif request.is_json:
        data = request.get_json(silent=True) or {}
        raw_intensity = data.get('intensity')

    if raw_intensity is not None:
        try:
            intensity = max(1, min(10, int(raw_intensity)))
        except (ValueError, TypeError):
            intensity = 7

    sanitized_res = cv_engine.sanitize_fingerprints(image_bytes, mode=mode, intensity=intensity)
    if sanitized_res is None:
        return jsonify({"error": "Sanitization failed on this image payload."}), 422

    return jsonify(sanitized_res)

# ---------------------------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------------------------
@app.errorhandler(413)
def payload_too_large(error):
    return jsonify({
        "error": f"Upload payload exceeds maximum allowable size ({MAX_FILE_MB}MB)."
    }), 413

@app.errorhandler(404)
def not_found_error(error):
    if request.path.startswith('/api/') or request.method == 'POST':
        return jsonify({"error": "Resource not found"}), 404
    return render_template('index.html', samples=SAMPLE_SCENARIOS), 404

@app.errorhandler(429)
def too_many_requests_error(error):
    return jsonify({
        "error": "Too Many Requests. System is throttling compute-intensive image processing."
    }), 429

@app.errorhandler(500)
def internal_server_error(error):
    return jsonify({
        "error": "Internal processing error. The server encountered an unexpected condition."
    }), 500

if __name__ == '__main__':
    # Default to secure local host binding and non-debug mode unless explicitly configured
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_PORT', 5000))

    print("=" * 65)
    print(" BioCypher 2.0 Hardened Biometric Forensics Suite Initializing ")
    print(f" Interface: http://{host}:{port}")
    print(f" Security: OWASP Headers Active | Rate Limiter Enforced")
    print(f" Debug Mode: {debug_mode}")
    print("=" * 65)
    app.run(debug=debug_mode, host=host, port=port)
