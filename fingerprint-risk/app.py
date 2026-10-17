"""
BioCypher 2.0 — Biometric Cybersecurity & Fingerprint Exposure Suite
===================================================================
Hardened Flask Backend Server providing:
- High-performance multi-spectral biometric CV forensics (/analyze)
- Active defense privacy redactor & ridge sanitizer (/sanitize)
- Preset sample scenario gallery (/api/samples)
- Administrative Security Operations Gateway (/admin)
- Comprehensive OWASP Top 10 defense & security hardening
"""

import os
import sys
import base64
import time
import secrets
import threading
import datetime
import urllib.request
import urllib.parse
import urllib.error
import ipaddress
from collections import defaultdict, deque
from functools import wraps

# Load environment variables securely from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from flask import (
    Flask, render_template, request, jsonify, make_response,
    session, redirect, url_for, abort
)
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import cv_engine

# ---------------------------------------------------------------------------
# Application Initialization & Security Configuration
# ---------------------------------------------------------------------------
app = Flask(__name__)

# Enforce strict 16MB upload limit
MAX_FILE_MB = 16
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_MB * 1024 * 1024

# Explicitly disable Flask debug and testing modes by default
app.config['DEBUG'] = False
app.config['TESTING'] = False

# Cryptographic Secret Key Configuration
_env_secret_key = os.environ.get('SECRET_KEY', '').strip()
if not _env_secret_key or _env_secret_key.startswith('replace-with'):
    # Ephemeral cryptographically strong secret token generated for session security
    SECRET_KEY = secrets.token_hex(32)
    _secret_is_ephemeral = True
else:
    SECRET_KEY = _env_secret_key
    _secret_is_ephemeral = False

app.config['SECRET_KEY'] = SECRET_KEY

# Session Cookie Hardening
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1', 't')
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=2)

# Directory Setup
UPLOAD_FOLDER = os.path.join('static', 'uploads')
SAMPLES_FOLDER = os.path.join('static', 'samples')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SAMPLES_FOLDER, exist_ok=True)

# ---------------------------------------------------------------------------
# Admin Credentials & Salted Password Hashing (PBKDF2:SHA-256)
# ---------------------------------------------------------------------------
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin').strip()
_env_admin_hash = os.environ.get('ADMIN_PASSWORD_HASH', '').strip()

if not _env_admin_hash or _env_admin_hash.startswith('pbkdf2:sha256:600000$replace'):
    # Default initial password if not configured in .env
    # PBKDF2 with SHA-256 and 600,000 iterations
    DEFAULT_ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'BioCypher2026!AdminSecured')
    ADMIN_PASSWORD_HASH = generate_password_hash(DEFAULT_ADMIN_PASSWORD, method='pbkdf2:sha256:600000')
    _admin_is_default_password = True
else:
    ADMIN_PASSWORD_HASH = _env_admin_hash
    _admin_is_default_password = False

# ---------------------------------------------------------------------------
# Thread-Safe Security Event Audit Logger
# ---------------------------------------------------------------------------
_AUDIT_LOG_CAPACITY = 250
_audit_logs = deque(maxlen=_AUDIT_LOG_CAPACITY)
_audit_lock = threading.Lock()

# Global Telemetry Counters
_telemetry = {
    "cv_scans_processed": 0,
    "sanitizations_processed": 0,
    "rate_limits_blocked": 0,
    "auth_success_count": 0,
    "auth_failure_count": 0
}
_telemetry_lock = threading.Lock()

def record_security_event(event_type, client_ip, details, severity="INFO"):
    """
    Records an immutable security audit event without logging PII or raw credentials.
    """
    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    event_entry = {
        "timestamp": timestamp,
        "event": str(event_type)[:32],
        "ip": str(client_ip)[:45],
        "severity": severity,
        "details": str(details)[:200]
    }
    with _audit_lock:
        _audit_logs.appendleft(event_entry)

# ---------------------------------------------------------------------------
# Multi-Tier Sliding Window Rate Limiting & DoS Defense
# ---------------------------------------------------------------------------
RATE_LIMIT_WINDOW = int(os.environ.get('RATE_LIMIT_WINDOW_SECONDS', 60))
RATE_LIMITS = {
    "global": int(os.environ.get('RATE_LIMIT_GLOBAL_MAX', 60)),     # general endpoints
    "cv_heavy": int(os.environ.get('RATE_LIMIT_HEAVY_CV_MAX', 15)),  # CPU-heavy CV endpoints
    "auth": int(os.environ.get('RATE_LIMIT_AUTH_MAX', 5))           # authentication attempts
}

_ip_request_history = defaultdict(lambda: defaultdict(list))
_failed_auth_history = defaultdict(list)
_rate_limit_lock = threading.Lock()

def check_rate_limit(client_ip, tier="global"):
    """
    Sliding window rate limiter enforcing multi-tier quotas.
    Returns (is_limited, retry_after_seconds, current_count, max_limit).
    """
    now = time.time()
    max_allowed = RATE_LIMITS.get(tier, 60)
    window = RATE_LIMIT_WINDOW

    with _rate_limit_lock:
        history = _ip_request_history[tier][client_ip]
        valid_history = [t for t in history if now - t < window]
        _ip_request_history[tier][client_ip] = valid_history

        if len(valid_history) >= max_allowed:
            retry_after = int(window - (now - valid_history[0])) + 1
            with _telemetry_lock:
                _telemetry["rate_limits_blocked"] += 1
            record_security_event(
                "RATE_LIMIT_BLOCKED",
                client_ip,
                f"Exceeded {tier} tier quota ({len(valid_history)}/{max_allowed})",
                severity="WARNING"
            )
            return True, max(1, retry_after), len(valid_history), max_allowed

        valid_history.append(now)
        _ip_request_history[tier][client_ip] = valid_history
        return False, 0, len(valid_history), max_allowed

def check_auth_lockout(client_ip):
    """
    Checks if client IP is temporarily locked out due to repeated failed logins.
    Lockout duration: 15 minutes (900 seconds) after 5 consecutive failed attempts.
    """
    now = time.time()
    lockout_window = 900
    max_fails = 5

    with _rate_limit_lock:
        fails = _failed_auth_history[client_ip]
        valid_fails = [t for t in fails if now - t < lockout_window]
        _failed_auth_history[client_ip] = valid_fails
        if len(valid_fails) >= max_fails:
            remaining_lockout = int(lockout_window - (now - valid_fails[0])) + 1
            return True, max(1, remaining_lockout)
        return False, 0

def record_auth_failure(client_ip):
    now = time.time()
    with _rate_limit_lock:
        _failed_auth_history[client_ip].append(now)
    with _telemetry_lock:
        _telemetry["auth_failure_count"] += 1
    record_security_event("AUTH_FAILURE", client_ip, "Invalid credentials submitted", severity="WARNING")

def record_auth_success(client_ip, username):
    now = time.time()
    with _rate_limit_lock:
        _failed_auth_history.pop(client_ip, None)
    with _telemetry_lock:
        _telemetry["auth_success_count"] += 1
    record_security_event("AUTH_SUCCESS", client_ip, f"User '{username}' authenticated", severity="INFO")

# ---------------------------------------------------------------------------
# CSRF Token Defense
# ---------------------------------------------------------------------------
def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(24)
    return session['_csrf_token']

def validate_csrf_token(token):
    session_token = session.get('_csrf_token')
    if not session_token or not token:
        return False
    return secrets.compare_digest(str(session_token), str(token))

app.jinja_env.globals['csrf_token'] = generate_csrf_token

# ---------------------------------------------------------------------------
# Role-Based Access Control (RBAC) Decorator
# ---------------------------------------------------------------------------
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user or not isinstance(user, dict) or user.get('role') != 'admin':
            client_ip = request.remote_addr or 'unknown'
            record_security_event("UNAUTHORIZED_ACCESS", client_ip, f"Blocked unauthorized attempt on {request.path}", severity="WARNING")
            if request.path.startswith('/api/'):
                return jsonify({"error": "Unauthorized. Administrative privileges required."}), 403
            return redirect(url_for('admin_login', next=request.path))
        return f(*args, **kwargs)
    return decorated_function

# ---------------------------------------------------------------------------
# CORS Configuration & Origin Whitelist
# ---------------------------------------------------------------------------
raw_origins = os.environ.get('ALLOWED_ORIGINS', '')
ALLOWED_ORIGINS = {o.strip() for o in raw_origins.split(',') if o.strip()}

# ---------------------------------------------------------------------------
# HTTP Security Headers (OWASP Top 10 Compliance)
# ---------------------------------------------------------------------------
@app.after_request
def apply_security_headers(response):
    """
    Attaches defense-in-depth security headers to every HTTP response.
    """
    # Prevent MIME sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    # Deprecated XSS auditor disabled in favor of CSP
    response.headers['X-XSS-Protection'] = '0'
    # Referrer privacy policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Hardware & feature permission boundary
    response.headers['Permissions-Policy'] = 'camera=(self), microphone=(), geolocation=(), payment=()'
    # Enforce HTTPS HSTS (1 year + subdomains)
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
    # Isolation headers
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
    # Mask server software signature
    response.headers['Server'] = 'BioCypher-Gateway/2.0'

    # Strict Content-Security-Policy (CSP)
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        "media-src 'self' blob:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none';"
    )
    response.headers['Content-Security-Policy'] = csp

    # Restricted CORS Policy
    req_origin = request.headers.get('Origin')
    if req_origin:
        if req_origin in ALLOWED_ORIGINS or req_origin == request.host_url.rstrip('/'):
            response.headers['Access-Control-Allow-Origin'] = req_origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, X-CSRF-Token'
    
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

    # 3. Check for sample_id with strict path traversal defense
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
                samples_dir_abs = os.path.abspath(SAMPLES_FOLDER)
                sample_path = os.path.abspath(os.path.join(samples_dir_abs, safe_fname))
                # Ensure path is strictly within samples folder
                if sample_path.startswith(samples_dir_abs) and os.path.isfile(sample_path):
                    with open(sample_path, 'rb') as f:
                        return f.read(), safe_fname

    return None, None

# ---------------------------------------------------------------------------
# Public Endpoints
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

@app.route('/api/ipcam/capture', methods=['POST'])
def capture_ipcam():
    """
    Fetches a single snapshot frame from an IP Webcam (e.g. phone running IP Webcam app).
    Enforces SSRF defense, scheme restriction (HTTP/HTTPS only), 5-second timeout,
    and image payload verification.
    """
    client_ip = request.remote_addr or 'unknown'
    is_limited, retry_after, _, _ = check_rate_limit(client_ip, tier="cv_heavy")
    if is_limited:
        return jsonify({
            "error": "Rate limit exceeded. Please wait before fetching more camera frames.",
            "retry_after_seconds": retry_after
        }), 429

    data = request.get_json(silent=True) or {}
    raw_url = str(data.get('url', '')).strip()

    if not raw_url:
        return jsonify({"error": "No IP Webcam URL provided."}), 400

    if not raw_url.startswith(('http://', 'https://')):
        raw_url = 'http://' + raw_url

    try:
        parsed = urllib.parse.urlparse(raw_url)
    except Exception:
        return jsonify({"error": "Malformed URL format."}), 400

    hostname = parsed.hostname
    if not hostname:
        return jsonify({"error": "Invalid IP address or hostname in URL."}), 400

    # SSRF Defense: Disallow cloud metadata and loopback addresses
    try:
        ip_obj = ipaddress.ip_address(hostname)
        if ip_obj.is_loopback or str(ip_obj) == "169.254.169.254":
            return jsonify({"error": "Security Restriction: Connecting to loopback or metadata services is prohibited."}), 403
    except ValueError:
        if hostname.lower() in ('localhost', '127.0.0.1', '::1', 'instance-data'):
            return jsonify({"error": "Security Restriction: Localhost loopback is not allowed for IP webcam."}), 403

    # Auto-resolve common IP Webcam snapshot endpoints if user entered only host:port
    target_url = raw_url
    if parsed.path in ('', '/'):
        # Check standard port signatures or default to /shot.jpg
        if parsed.port == 4747: # DroidCam
            target_url = urllib.parse.urljoin(raw_url, '/cam/1/frame.jpg')
        else:
            target_url = urllib.parse.urljoin(raw_url, '/shot.jpg')

    try:
        import ssl
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        # Retry up to 3 times for intermittent Wi-Fi connections
        image_bytes = None
        last_error = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    target_url,
                    headers={'User-Agent': 'BioCypher-IPCam/2.0'}
                )
                with urllib.request.urlopen(req, timeout=5, context=ssl_ctx) as response:
                    image_bytes = response.read(MAX_FILE_MB * 1024 * 1024)
                if image_bytes and len(image_bytes) >= 12:
                    break
            except Exception as retry_err:
                last_error = retry_err
                if attempt < 2:
                    time.sleep(0.8)

        if not image_bytes or len(image_bytes) < 12:
            error_detail = str(last_error)[:100] if last_error else "Empty response"
            return jsonify({"error": f"Cannot reach phone at {target_url} after 3 attempts. Detail: {error_detail}. Ensure the IP Webcam app is running and your phone is awake."}), 502

        # Verify magic byte header (JPEG, PNG, WEBP)
        is_valid = (
            image_bytes[:3] == b'\xff\xd8\xff' or
            image_bytes[:8] == b'\x89PNG\r\n\x1a\n' or
            (image_bytes[:4] == b'RIFF' and len(image_bytes) > 12 and image_bytes[8:12] == b'WEBP')
        )
        if not is_valid:
            return jsonify({"error": f"Connected to {target_url}, but the response was not a valid image. Ensure you are using the snapshot URL (e.g., /shot.jpg)."}), 422

        b64_str = base64.b64encode(image_bytes).decode('utf-8')
        data_uri = f"data:image/jpeg;base64,{b64_str}"
        return jsonify({
            "status": "success",
            "image_b64": data_uri,
            "filename": f"ipcam_{int(time.time())}.jpg"
        })
    except urllib.error.URLError as e:
        return jsonify({"error": f"Cannot reach phone at {target_url}. Ensure your phone & PC are on the same Wi-Fi network and the IP Webcam app is running. ({str(e)[:80]})"}), 502
    except Exception as e:
        return jsonify({"error": f"Connection failed: {str(e)[:80]}"}), 504

@app.route('/analyze', methods=['POST'])
def analyze():
    """
    Full biometric exposure & minutiae diagnostic endpoint.
    Protected by sliding-window rate limiting, magic byte verification, and decompression bomb defenses.
    """
    client_ip = request.remote_addr or 'unknown'
    is_limited, retry_after, current_cnt, max_limit = check_rate_limit(client_ip, tier="cv_heavy")
    if is_limited:
        resp = jsonify({
            "error": "Rate limit exceeded. Too many forensic scans requested.",
            "retry_after_seconds": retry_after
        })
        resp.status_code = 429
        resp.headers['Retry-After'] = str(retry_after)
        resp.headers['X-RateLimit-Limit'] = str(max_limit)
        resp.headers['X-RateLimit-Remaining'] = "0"
        resp.headers['X-RateLimit-Reset'] = str(int(time.time() + retry_after))
        return resp

    image_bytes, filename = extract_image_bytes(request)
    if not image_bytes:
        record_security_event("INVALID_PAYLOAD", client_ip, "Empty or invalid image submission", severity="WARNING")
        return jsonify({
            "error": "No valid image provided. Please upload an image file, capture via webcam, or choose a benchmark preset."
        }), 400

    results = cv_engine.analyze_image_forensics(image_bytes)
    if results is None:
        record_security_event("DECODE_FAILURE", client_ip, "Image payload failed validation or decompression check", severity="WARNING")
        return jsonify({
            "error": "Image validation failed. The payload is either corrupt, unreadable, or not a supported image format (JPEG, PNG, WEBP, BMP)."
        }), 422

    with _telemetry_lock:
        _telemetry["cv_scans_processed"] += 1

    results["filename"] = sanitize_output_filename(filename)
    return jsonify(results)

@app.route('/sanitize', methods=['POST'])
def sanitize():
    """
    Active Defense Endpoint:
    Sanitizes detected finger/hand regions with adaptive blur, cyber mosaic, or adversarial scramble.
    """
    client_ip = request.remote_addr or 'unknown'
    is_limited, retry_after, current_cnt, max_limit = check_rate_limit(client_ip, tier="cv_heavy")
    if is_limited:
        resp = jsonify({
            "error": "Rate limit exceeded. Please wait before submitting additional sanitization requests.",
            "retry_after_seconds": retry_after
        })
        resp.status_code = 429
        resp.headers['Retry-After'] = str(retry_after)
        resp.headers['X-RateLimit-Limit'] = str(max_limit)
        resp.headers['X-RateLimit-Remaining'] = "0"
        resp.headers['X-RateLimit-Reset'] = str(int(time.time() + retry_after))
        return resp

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

    with _telemetry_lock:
        _telemetry["sanitizations_processed"] += 1

    return jsonify(sanitized_res)

# ---------------------------------------------------------------------------
# Admin & Security Operations Portal
# ---------------------------------------------------------------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """
    Administrative Login Gateway protected by:
    - Brute force lockout (15 minutes after 5 failures)
    - IP sliding-window rate limit
    - CSRF token validation
    - Salted constant-time password verification
    """
    client_ip = request.remote_addr or 'unknown'
    next_url = request.args.get('next') or request.form.get('next') or '/admin'
    # Restrict next_url redirection to local relative path (prevent open redirect vulnerability)
    if not next_url.startswith('/') or next_url.startswith('//'):
        next_url = '/admin'

    if request.method == 'GET':
        if session.get('user', {}).get('role') == 'admin':
            return redirect(next_url)
        return render_template('admin_login.html', error=None, next_url=next_url, csrf_token=generate_csrf_token())

    # Rate limiting on auth
    is_locked, remaining_lock = check_auth_lockout(client_ip)
    if is_locked:
        record_security_event("AUTH_LOCKOUT", client_ip, f"Blocked login attempt during lockout ({remaining_lock}s remaining)", severity="CRITICAL")
        return render_template(
            'admin_login.html',
            error=f"Too many failed login attempts. IP temporarily locked out for {remaining_lock} seconds.",
            next_url=next_url,
            csrf_token=generate_csrf_token()
        ), 429

    # CSRF verification
    csrf_token = request.form.get('csrf_token')
    if not validate_csrf_token(csrf_token):
        record_security_event("CSRF_REJECTED", client_ip, "Invalid or missing CSRF token on admin login", severity="WARNING")
        return render_template('admin_login.html', error="Invalid security session token. Please try again.", next_url=next_url, csrf_token=generate_csrf_token()), 400

    username = str(request.form.get('username', '')).strip()
    password = str(request.form.get('password', ''))

    # Verify username & password using PBKDF2:SHA-256
    username_valid = secrets.compare_digest(username.lower(), ADMIN_USERNAME.lower())
    password_valid = check_password_hash(ADMIN_PASSWORD_HASH, password)

    if username_valid and password_valid:
        # Prevent Session Fixation: clear and regenerate session
        session.clear()
        session['user'] = {
            "username": ADMIN_USERNAME,
            "role": "admin",
            "authenticated_at": time.time()
        }
        generate_csrf_token()
        record_auth_success(client_ip, ADMIN_USERNAME)
        return redirect(next_url)
    else:
        record_auth_failure(client_ip)
        return render_template('admin_login.html', error="Invalid administrator credentials.", next_url=next_url, csrf_token=generate_csrf_token()), 401

@app.route('/admin/logout', methods=['GET', 'POST'])
def admin_logout():
    client_ip = request.remote_addr or 'unknown'
    username = session.get('user', {}).get('username', 'admin')
    session.clear()
    record_security_event("AUTH_LOGOUT", client_ip, f"User '{username}' logged out", severity="INFO")
    return redirect(url_for('admin_login'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    """
    Administrative Security Operations Dashboard.
    Provides sanitized environmental audits, telemetry counters, and real-time logs.
    """
    with _telemetry_lock:
        scans_count = _telemetry["cv_scans_processed"]
        rate_blocked = _telemetry["rate_limits_blocked"]

    # Gather sanitized environment status
    secret_key_status = "EPHEMERAL (AUTO-GENERATED 256-BIT)" if _secret_is_ephemeral else "PERSISTED (FROM ENVIRONMENT)"
    cors_status = f"RESTRICTED ({len(ALLOWED_ORIGINS)} Allowed Origins)" if ALLOWED_ORIGINS else "STRICT SAME-ORIGIN ONLY"

    with _audit_lock:
        recent_logs = list(_audit_logs)[:40]

    # Gather currently tracked client IPs
    active_ips = []
    now = time.time()
    with _rate_limit_lock:
        for ip, timestamps in _ip_request_history['cv_heavy'].items():
            valid = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
            if valid:
                active_ips.append({
                    "ip": ip,
                    "count": len(valid),
                    "is_limited": len(valid) >= RATE_LIMITS['cv_heavy']
                })

    return render_template(
        'admin.html',
        username=session.get('user', {}).get('username', 'admin'),
        cv_scans_processed=scans_count,
        rate_limits_blocked=rate_blocked,
        secret_key_status=secret_key_status,
        cors_status=cors_status,
        audit_logs=recent_logs,
        active_ips=active_ips,
        rate_limits=RATE_LIMITS,
        csrf_token=generate_csrf_token()
    )

@app.route('/api/admin/metrics', methods=['GET'])
@admin_required
def admin_metrics():
    """Administrative JSON telemetry endpoint."""
    with _telemetry_lock:
        telemetry_copy = dict(_telemetry)
    return jsonify({
        "status": "success",
        "telemetry": telemetry_copy,
        "rate_limits": RATE_LIMITS,
        "debug_mode": app.config.get('DEBUG', False),
        "environment": os.environ.get('FLASK_ENV', 'production')
    })

@app.route('/api/admin/audit-logs', methods=['GET'])
@admin_required
def admin_audit_logs():
    """Administrative JSON audit log endpoint."""
    with _audit_lock:
        logs_copy = list(_audit_logs)
    return jsonify({
        "status": "success",
        "total_records": len(logs_copy),
        "logs": logs_copy
    })

@app.route('/api/admin/clear-rate-limits', methods=['POST'])
@admin_required
def clear_rate_limits():
    """Flushes active rate-limiting windows upon authenticated admin command."""
    client_ip = request.remote_addr or 'unknown'
    csrf = request.form.get('csrf_token')
    if not validate_csrf_token(csrf):
        return jsonify({"error": "Invalid CSRF token"}), 400

    with _rate_limit_lock:
        _ip_request_history.clear()
        _failed_auth_history.clear()

    record_security_event("RATE_LIMIT_RESET", client_ip, "Administrator flushed rate limit windows", severity="WARNING")
    return redirect(url_for('admin_dashboard'))

# ---------------------------------------------------------------------------
# Error Handlers (Sanitized Output & No Leaked Stack Traces)
# ---------------------------------------------------------------------------
@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        "error": "Bad Request. The request parameters or payload format are invalid."
    }), 400

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({
        "error": "Authentication Required. Please log in with valid credentials."
    }), 401

@app.errorhandler(403)
def forbidden(error):
    return jsonify({
        "error": "Forbidden. You do not have permission to access this resource."
    }), 403

@app.errorhandler(404)
def not_found_error(error):
    if request.path.startswith('/api/') or request.method == 'POST':
        return jsonify({"error": "Resource not found"}), 404
    return render_template('index.html', samples=SAMPLE_SCENARIOS), 404

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        "error": "Method Not Allowed on this endpoint."
    }), 405

@app.errorhandler(413)
def payload_too_large(error):
    return jsonify({
        "error": f"Upload payload exceeds maximum allowable size ({MAX_FILE_MB}MB)."
    }), 413

@app.errorhandler(422)
def unprocessable_entity(error):
    return jsonify({
        "error": "Unprocessable entity. The payload could not be decoded or processed."
    }), 422

@app.errorhandler(429)
def too_many_requests_error(error):
    return jsonify({
        "error": "Too Many Requests. System is throttling requests to prevent resource exhaustion."
    }), 429

@app.errorhandler(500)
def internal_server_error(error):
    # Log internally without displaying stack traces to the user
    client_ip = request.remote_addr or 'unknown'
    record_security_event("INTERNAL_SERVER_ERROR", client_ip, f"Exception on {request.path}", severity="CRITICAL")
    return jsonify({
        "error": "An unexpected error occurred during processing. The incident has been logged."
    }), 500

# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    # Debug mode explicitly controlled via environment, defaulting strictly to False
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    port = int(os.environ.get('PORT', os.environ.get('FLASK_PORT', 5000)))
    host = os.environ.get('FLASK_HOST', '0.0.0.0')

    # Detect local LAN IP for display
    local_ip = '127.0.0.1'
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass

    print("=" * 70)
    print(" BioCypher 2.0 Hardened Biometric Cybersecurity Suite Starting ")
    print(f" Local:    http://127.0.0.1:{port}")
    if host == '0.0.0.0':
        print(f" Network:  http://{local_ip}:{port}  ← Open this on your phone!")
    print(f" Admin:    http://127.0.0.1:{port}/admin")
    print(f" Security: OWASP Headers | Multi-Tier Rate Limiter | PBKDF2:SHA-256")
    print(f" Debug Mode: {debug_mode} (Strictly Enforced)")
    if _secret_is_ephemeral:
        print(" [SECURITY NOTICE] Ephemeral SECRET_KEY generated. Set SECRET_KEY in .env")
    if _admin_is_default_password:
        print(" [SECURITY NOTICE] Default admin password active. Set ADMIN_PASSWORD_HASH in .env")
    print("=" * 70)

    app.run(debug=debug_mode, host=host, port=port)
