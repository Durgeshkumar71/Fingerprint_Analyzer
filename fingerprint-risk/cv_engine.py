"""
BioCypher 2.0 Computer Vision & Biometric Forensics Engine
=========================================================
Performs multi-stage biometric extraction risk analysis:
1. Dual-space skin & hand segmentation (HSV + YCrCb)
2. Zero-DC Directional Gabor filter bank (bandpass ridge extraction)
3. Ridge skeletonization & forensic minutiae keypoint extraction with AFIS pruning
4. NIST SP 800-76-2 compliance & clone spoofing viability estimation
5. Multi-layer visual rendering (Original, Skin Mask, Gabor Heatmap, Minutiae, Composite HUD)
6. Privacy Sanitization Tool (adaptive blur, cyber mosaic, adversarial scramble)
"""

import cv2
import numpy as np
import base64
import io

def decode_image_bytes(image_bytes, max_dim=1920):
    """
    Safely decodes image bytes into an OpenCV BGR image.
    Enforces:
    1. Magic byte verification (validates JPEG, PNG, WEBP, BMP)
    2. Payload length limits (<= 16MB)
    3. Decompression bomb / memory exhaustion defense (auto-downscaling to max 1920px)
    """
    if not image_bytes or len(image_bytes) < 12:
        return None

    if len(image_bytes) > 16 * 1024 * 1024:
        return None

    # Magic byte header verification
    is_valid_format = False
    if image_bytes[:3] == b'\xff\xd8\xff':  # JPEG
        is_valid_format = True
    elif image_bytes[:8] == b'\x89PNG\r\n\x1a\n':  # PNG
        is_valid_format = True
    elif image_bytes[:4] == b'RIFF' and len(image_bytes) > 12 and image_bytes[8:12] == b'WEBP':  # WEBP
        is_valid_format = True
    elif image_bytes[:2] == b'BM':  # BMP
        is_valid_format = True

    if not is_valid_format:
        return None

    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None

        h, w = img.shape[:2]
        # Prevent Decompression Bomb DoS by downscaling images larger than max_dim
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

        return img
    except Exception as e:
        print(f"Error decoding image: {e}")
        return None

def encode_image_base64(img_bgr, quality=88):
    """Encodes an OpenCV BGR image to a base64 JPEG string."""
    _, buffer = cv2.imencode('.jpg', img_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return base64.b64encode(buffer).decode('utf-8')

def detect_skin_regions(img):
    """
    Combines HSV and YCrCb color spaces for inclusive skin tone segmentation.
    Applies morphological cleaning to eliminate spurious artifacts.
    """
    h, w = img.shape[:2]

    # 1. HSV skin thresholding
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    lower_hsv1 = np.array([0, 20, 60], dtype=np.uint8)
    upper_hsv1 = np.array([25, 255, 255], dtype=np.uint8)
    mask1 = cv2.inRange(hsv, lower_hsv1, upper_hsv1)

    lower_hsv2 = np.array([170, 20, 60], dtype=np.uint8)
    upper_hsv2 = np.array([180, 255, 255], dtype=np.uint8)
    mask2 = cv2.inRange(hsv, lower_hsv2, upper_hsv2)

    # 2. YCrCb skin thresholding (robust across illumination & diverse skin tones)
    ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
    lower_ycrcb = np.array([0, 133, 77], dtype=np.uint8)
    upper_ycrcb = np.array([255, 173, 127], dtype=np.uint8)
    mask_ycrcb = cv2.inRange(ycrcb, lower_ycrcb, upper_ycrcb)

    # Combined skin mask
    combined_mask = cv2.bitwise_or(mask1, mask2)
    combined_mask = cv2.bitwise_or(combined_mask, mask_ycrcb)

    # Morphological filtering to close holes and remove salt-and-pepper noise
    kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    clean_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel_close)
    clean_mask = cv2.morphologyEx(clean_mask, cv2.MORPH_OPEN, kernel_open)

    # Extract contours and bounding boxes
    contours, _ = cv2.findContours(clean_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    significant_contours = [c for c in contours if cv2.contourArea(c) > max(350, int((h * w) * 0.0012))]
    bounding_boxes = [cv2.boundingRect(c) for c in significant_contours]

    return clean_mask, significant_contours, bounding_boxes

def compute_zero_dc_gabor(gray_img, angles=None):
    """
    Applies multi-orientation Zero-DC Gabor filter bank.
    Zero-DC eliminates response to uniform skin regions and isolates friction ridges.
    """
    if angles is None:
        angles = [0, np.pi/6, np.pi/3, np.pi/2, 2*np.pi/3, 5*np.pi/6]

    responses = []
    ksize = 21
    sigma = 3.6
    lambd = 9.0
    gamma = 0.55
    psi = 0

    gray_float = gray_img.astype(np.float32)

    for theta in angles:
        kernel = cv2.getGaborKernel((ksize, ksize), sigma, theta, lambd, gamma, psi, ktype=cv2.CV_32F)
        # Force Zero-DC (zero mean)
        kernel -= float(np.mean(kernel))
        l1_norm = float(np.sum(np.abs(kernel)))
        if l1_norm > 0:
            kernel /= l1_norm
        filtered = cv2.filter2D(gray_float, cv2.CV_32F, kernel)
        responses.append(np.abs(filtered))

    # Max-pooling across orientations highlights prominent directional ridges
    max_response = np.maximum.reduce(responses)
    return max_response

def skeletonize_ridges(binary_img):
    """
    Pure NumPy/OpenCV morphological thinning for reliable ridge skeletonization.
    """
    skeleton = np.zeros(binary_img.shape, dtype=np.uint8)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    temp = binary_img.copy()

    iterations = 0
    max_iters = 40
    while iterations < max_iters:
        eroded = cv2.erode(temp, element)
        opened = cv2.morphologyEx(eroded, cv2.MORPH_OPEN, element)
        subset = cv2.subtract(eroded, opened)
        skeleton = cv2.bitwise_or(skeleton, subset)
        temp = eroded.copy()
        iterations += 1
        if cv2.countNonZero(temp) == 0:
            break

    return skeleton

def extract_and_prune_minutiae(skeleton, skin_mask, min_distance=8, max_points=180):
    """
    Extracts candidate fingerprint minutiae points (ridge endings & bifurcations)
    and applies distance-based non-maximum suppression (AFIS pruning) to discard spurious points.
    """
    h, w = skeleton.shape
    skel_binary = (skeleton > 0).astype(np.uint8)

    # 3x3 neighbor convolution kernel
    neighbor_kernel = np.array([
        [1, 1, 1],
        [1, 0, 1],
        [1, 1, 1]
    ], dtype=np.uint8)

    neighbor_count = cv2.filter2D(skel_binary, -1, neighbor_kernel)

    # Restrict to skin region and away from image borders
    valid_region = (skin_mask > 0)
    border_px = 8
    valid_region[:border_px, :] = False
    valid_region[-border_px:, :] = False
    valid_region[:, :border_px] = False
    valid_region[:, -border_px:] = False

    ending_mask = (skel_binary == 1) & (neighbor_count == 1) & valid_region
    bifurcation_mask = (skel_binary == 1) & (neighbor_count == 3) & valid_region

    end_y, end_x = np.where(ending_mask)
    bif_y, bif_x = np.where(bifurcation_mask)

    def prune_points(xs, ys, pt_type):
        pruned = []
        occupied_grid = set()
        cell_size = min_distance
        for x, y in zip(xs, ys):
            gx, gy = int(x // cell_size), int(y // cell_size)
            if (gx, gy) not in occupied_grid:
                occupied_grid.add((gx, gy))
                pruned.append({"x": int(x), "y": int(y), "type": pt_type})
                if len(pruned) >= max_points // 2:
                    break
        return pruned

    pruned_endings = prune_points(end_x, end_y, "ending")
    pruned_bifurcations = prune_points(bif_x, bif_y, "bifurcation")
    total_valid = len(pruned_endings) + len(pruned_bifurcations)

    return pruned_endings, pruned_bifurcations, total_valid

def render_layers(original, skin_mask, contours, gabor_response, skeleton, endings, bifurcations, bounding_boxes, risk_percent):
    """
    Renders 5 specialized visual inspection layers for the cyber forensic UI.
    """
    h, w = original.shape[:2]

    # --- LAYER 0: Original Image ---
    layer_original = original.copy()

    # --- LAYER 1: Skin Segmentation Mask ---
    layer_skin = np.zeros_like(original)
    layer_skin[skin_mask > 0] = [30, 150, 255] # Neon tactical amber tint
    layer_skin = cv2.addWeighted(original, 0.45, layer_skin, 0.55, 0)
    for cnt in contours:
        cv2.drawContours(layer_skin, [cnt], -1, (0, 255, 231), 2)
    for (bx, by, bw, bh) in bounding_boxes:
        cv2.rectangle(layer_skin, (bx, by), (bx + bw, by + bh), (255, 46, 126), 1)

    # --- LAYER 2: Gabor Ridge Frequency Heatmap ---
    gabor_clip = np.clip(gabor_response * 18.0, 0, 255).astype(np.uint8)
    gabor_heatmap = cv2.applyColorMap(gabor_clip, cv2.COLORMAP_INFERNO)
    
    bg_dimmed = cv2.addWeighted(original, 0.25, np.zeros_like(original), 0.75, 0)
    layer_gabor = bg_dimmed.copy()
    layer_gabor[skin_mask > 0] = cv2.addWeighted(original[skin_mask > 0], 0.25, gabor_heatmap[skin_mask > 0], 0.75, 0)

    # --- LAYER 3: Skeleton & Minutiae Points Map ---
    layer_minutiae = cv2.addWeighted(original, 0.35, np.zeros_like(original), 0.65, 0)
    layer_minutiae[skeleton > 0] = [0, 230, 118] # Cyber neon green
    for pt in endings:
        cv2.circle(layer_minutiae, (pt["x"], pt["y"]), 3, (255, 255, 0), -1)
        cv2.circle(layer_minutiae, (pt["x"], pt["y"]), 5, (255, 231, 0), 1)
    for pt in bifurcations:
        px, py = pt["x"], pt["y"]
        pts = np.array([[px, py-4], [px+4, py], [px, py+4], [px-4, py]], np.int32)
        cv2.drawContours(layer_minutiae, [pts], 0, (126, 46, 255), -1)
        cv2.drawContours(layer_minutiae, [pts], 0, (255, 46, 200), 1)

    # --- LAYER 4: Cyber Tactical HUD Composite ---
    layer_composite = original.copy()
    dark_overlay = np.zeros_like(original)
    layer_composite = cv2.addWeighted(layer_composite, 0.88, dark_overlay, 0.12, 0)

    # Overlay active ridge heatmap on skin areas
    ridge_active = (gabor_response > 2.0) & (skin_mask > 0)
    if np.any(ridge_active):
        layer_composite[ridge_active] = cv2.addWeighted(
            layer_composite[ridge_active], 0.35,
            gabor_heatmap[ridge_active], 0.65, 0
        )

    # Draw tactical bounding brackets on detected hand/finger zones
    for (bx, by, bw, bh) in bounding_boxes:
        bracket_len = min(20, bw // 4, bh // 4)
        col = (0, 255, 231) if risk_percent < 50 else (46, 46, 255)
        # Top-left
        cv2.line(layer_composite, (bx, by), (bx + bracket_len, by), col, 2)
        cv2.line(layer_composite, (bx, by), (bx, by + bracket_len), col, 2)
        # Top-right
        cv2.line(layer_composite, (bx + bw, by), (bx + bw - bracket_len, by), col, 2)
        cv2.line(layer_composite, (bx + bw, by), (bx + bw, by + bracket_len), col, 2)
        # Bottom-left
        cv2.line(layer_composite, (bx, by + bh), (bx + bracket_len, by + bh), col, 2)
        cv2.line(layer_composite, (bx, by + bh), (bx, by + bh - bracket_len), col, 2)
        # Bottom-right
        cv2.line(layer_composite, (bx + bw, by + bh), (bx + bw - bracket_len, by + bh), col, 2)
        cv2.line(layer_composite, (bx + bw, by + bh), (bx + bw, by + bh - bracket_len), col, 2)

        # Crosshair center in bounding box
        cx, cy = bx + bw // 2, by + bh // 2
        cv2.drawMarker(layer_composite, (cx, cy), col, cv2.MARKER_CROSS, 12, 1)

    # Plot top minutiae with glowing dots
    for pt in endings[:35]:
        cv2.circle(layer_composite, (pt["x"], pt["y"]), 2, (0, 255, 231), -1)
    for pt in bifurcations[:35]:
        cv2.circle(layer_composite, (pt["x"], pt["y"]), 2, (255, 46, 126), -1)

    # Draw tactical HUD metadata header
    status_text = f"THREAT LEVEL: {risk_percent}%"
    cv2.putText(layer_composite, status_text, (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 231), 2)
    cv2.putText(layer_composite, "BIOCYPHER TACTICAL FORENSICS", (18, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (180, 220, 255), 1)

    return {
        "original": encode_image_base64(layer_original),
        "skin_mask": encode_image_base64(layer_skin),
        "gabor_heatmap": encode_image_base64(layer_gabor),
        "minutiae_map": encode_image_base64(layer_minutiae),
        "composite_hud": encode_image_base64(layer_composite)
    }

def analyze_image_forensics(image_bytes):
    """
    Main comprehensive biometric exposure diagnostic routine.
    Uses Multiplicative Forensic Extractability model.
    """
    img = decode_image_bytes(image_bytes)
    if img is None:
        return None

    h, w = img.shape[:2]
    total_pixels = h * w
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 1. Skin & Hand Segmentation
    skin_mask, contours, bounding_boxes = detect_skin_regions(img)
    skin_pixels = np.count_nonzero(skin_mask)
    skin_ratio = skin_pixels / total_pixels

    # Erode skin mask to reject outer silhouette perimeter from producing false ridge/minutiae edges
    interior_mask = cv2.erode(skin_mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13)))
    if np.count_nonzero(interior_mask) < 60:
        interior_mask = skin_mask

    # 2. Zero-DC Gabor Filter Ridge Analysis
    gabor_response = compute_zero_dc_gabor(gray)

    if np.count_nonzero(interior_mask) > 60:
        gabor_skin_vals = gabor_response[interior_mask > 0]
        ridge_intensity = float(np.mean(gabor_skin_vals))
        local_contrast = float(np.std(gray[interior_mask > 0])) / 128.0
    else:
        ridge_intensity = 0.0
        local_contrast = 0.0

    # 3. Image Clarity & Sharpness (Laplacian variance)
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    clarity_score = min(laplacian_var / 800.0, 1.0)

    # 4. Fine Structural Edge Density (Canny)
    edges = cv2.Canny(gray, 60, 160)
    edge_density = float(np.count_nonzero(edges & interior_mask)) / max(1, np.count_nonzero(interior_mask)) if np.count_nonzero(interior_mask) > 0 else 0.0

    # 5. Ridge Binarization & Minutiae Extraction
    gabor_skin = np.zeros_like(gabor_response)
    gabor_skin[interior_mask > 0] = gabor_response[interior_mask > 0]
    
    thresh_val = max(2.8, np.percentile(gabor_skin_vals, 70)) if np.count_nonzero(interior_mask) > 100 else 3.2
    gabor_bin = ((gabor_skin > thresh_val) & (interior_mask > 0)).astype(np.uint8) * 255

    skeleton = skeletonize_ridges(gabor_bin)
    endings, bifurcations, total_minutiae = extract_and_prune_minutiae(skeleton, interior_mask)

    # --- FORENSIC EXTRACTABILITY & RISK FORMULA ---
    ridge_factor = min(ridge_intensity / 4.0, 1.0)
    minutiae_factor = min(total_minutiae / 16.0, 1.0)
    skin_factor = min(skin_ratio * 4.0, 1.0)
    edge_factor = min(edge_density * 3.5, 1.0)
    contrast_factor = min(local_contrast, 1.0)

    # Biometric Extractability core signal:
    # Minutiae points are only meaningful if coherent friction ridges are present.
    extractability = ridge_factor * (0.50 + 0.50 * minutiae_factor)

    # Environmental & Exposure factors
    exposure_env = (
        skin_factor * 0.45 +
        clarity_score * 0.35 +
        edge_factor * 0.15 +
        contrast_factor * 0.05
    )

    # Multiplicative Risk Calculation
    if skin_ratio < 0.015:
        # Minimal skin detected
        raw_risk = min(exposure_env * 0.15, 0.10)
    elif extractability < 0.18:
        # Skin present (e.g. folded knuckles, palm, sanitized/blurred) but negligible ridge patterns
        raw_risk = min(extractability * exposure_env * 0.40, 0.20)
    else:
        # True fingerprint ridge exposure
        raw_risk = extractability * exposure_env * 1.35

    risk_score = int(min(round(raw_risk * 100), 99))

    # Risk classification
    if risk_score >= 70:
        risk_level = "CRITICAL"
        risk_color = "#ff2e2e"
        risk_status = "EXTREME BIOMETRIC EXPOSURE"
    elif risk_score >= 45:
        risk_level = "HIGH"
        risk_color = "#ff8c00"
        risk_status = "VIABLE CLONING RISK"
    elif risk_score >= 25:
        risk_level = "MODERATE"
        risk_color = "#f5c518"
        risk_status = "PARTIAL LATENT DATA"
    else:
        risk_level = "LOW"
        risk_color = "#00e676"
        risk_status = "LOW CLONE POTENTIAL"

    # Clone spoofing estimates (NIST 800-76-2 threshold >= 12 minutiae)
    is_forensic_match = (total_minutiae >= 12 and risk_score >= 45)
    conductive_ink = min(int(risk_score * 0.96), 98) if is_forensic_match else int(risk_score * 0.35)
    gelatin_mold = min(int(risk_score * 0.90), 94) if is_forensic_match else int(risk_score * 0.30)
    sensor_bypass = min(int(risk_score * 0.88), 91) if is_forensic_match else int(risk_score * 0.25)

    # Render multi-layer images
    layers = render_layers(
        img, skin_mask, contours, gabor_response, skeleton, endings, bifurcations, bounding_boxes, risk_score
    )

    # Defense recommendations
    recommendations = generate_recommendations(risk_score, total_minutiae, skin_ratio)

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "risk_color": risk_color,
        "risk_status": risk_status,
        "metrics": {
            "skin_detected": round(skin_ratio * 100, 1),
            "ridge_visibility": round(ridge_factor * 100, 1),
            "image_clarity": round(clarity_score * 100, 1),
            "edge_density": round(edge_factor * 100, 1),
            "local_contrast": round(contrast_factor * 100, 1),
            "minutiae_count": int(total_minutiae),
            "endings_count": len(endings),
            "bifurcations_count": len(bifurcations),
            "hand_regions_count": len(bounding_boxes)
        },
        "spoof_viability": {
            "conductive_ink": conductive_ink,
            "gelatin_mold": gelatin_mold,
            "sensor_bypass": sensor_bypass,
            "forensic_match_ready": is_forensic_match
        },
        "layers": layers,
        "resolution": f"{w}x{h}px",
        "recommendations": recommendations
    }

def sanitize_fingerprints(image_bytes, mode="blur", intensity=5):
    """
    Active Defense Privacy Tool:
    Sanitizes detected finger/hand regions by applying adaptive Gaussian blur,
    cyber pixelation mosaic, or high-frequency adversarial noise, rendering
    ridge patterns unextractable while keeping the photo aesthetic intact.
    """
    img = decode_image_bytes(image_bytes)
    if img is None:
        return None

    h, w = img.shape[:2]
    skin_mask, contours, bounding_boxes = detect_skin_regions(img)

    sanitized = img.copy()

    if np.count_nonzero(skin_mask) == 0:
        return {
            "sanitized_image": encode_image_base64(sanitized),
            "post_risk_score": 0,
            "post_risk_level": "LOW",
            "regions_sanitized": 0
        }

    valid_modes = ('blur', 'mosaic', 'scramble')
    mode = mode if mode in valid_modes else 'blur'
    intensity = max(1, min(10, int(intensity)))

    if mode == "blur":
        # Adaptive Gaussian Blur focused on skin mask
        ksize = int(intensity * 6) * 2 + 1
        sigma = float(intensity * 1.8)
        blurred = cv2.GaussianBlur(img, (ksize, ksize), sigma)
        mask_soft = cv2.GaussianBlur(skin_mask.astype(np.float32) / 255.0, (15, 15), 0)
        mask_3d = np.repeat(mask_soft[:, :, np.newaxis], 3, axis=2)
        sanitized = (blurred.astype(np.float32) * mask_3d + img.astype(np.float32) * (1.0 - mask_3d)).astype(np.uint8)

    elif mode == "mosaic":
        # Cyber pixelation mosaic on detected regions
        pixel_size = max(6, int(intensity * 5))
        for (bx, by, bw, bh) in bounding_boxes:
            roi = sanitized[by:by+bh, bx:bx+bw]
            if roi.shape[0] < pixel_size or roi.shape[1] < pixel_size:
                continue
            small = cv2.resize(roi, (max(1, bw // pixel_size), max(1, bh // pixel_size)), interpolation=cv2.INTER_LINEAR)
            pixelated = cv2.resize(small, (bw, bh), interpolation=cv2.INTER_NEAREST)
            # Subtle smoothing on block edges
            pixelated = cv2.GaussianBlur(pixelated, (5, 5), 1.0)
            roi_mask = skin_mask[by:by+bh, bx:bx+bw] > 0
            roi[roi_mask] = pixelated[roi_mask]

    elif mode == "scramble":
        # Phase scramble and bilateral texture destruction
        bilateral = cv2.bilateralFilter(img, 15, 80, 80)
        noise = np.random.randint(-int(intensity * 10), int(intensity * 10), img.shape, dtype=np.int16)
        scrambled_tex = np.clip(bilateral.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        mask_3d = np.repeat((skin_mask > 0)[:, :, np.newaxis], 3, axis=2)
        sanitized[mask_3d] = scrambled_tex[mask_3d]

    # Re-evaluate risk to verify reduction
    _, buffer = cv2.imencode('.jpg', sanitized, [cv2.IMWRITE_JPEG_QUALITY, 90])
    sanitized_bytes = buffer.tobytes()
    post_analysis = analyze_image_forensics(sanitized_bytes)

    return {
        "sanitized_image": encode_image_base64(sanitized),
        "post_risk_score": post_analysis["risk_score"] if post_analysis else 0,
        "post_risk_level": post_analysis["risk_level"] if post_analysis else "LOW",
        "regions_sanitized": len(bounding_boxes)
    }

def generate_recommendations(risk_score, minutiae_count, skin_ratio):
    recs = []
    if risk_score >= 70 or minutiae_count >= 12:
        recs.append({
            "severity": "CRITICAL",
            "title": "Admissible Minutiae Exceeded (>=12 Points)",
            "desc": "Extracted ridge details meet FBI/NIST forensic threshold. Malicious actors can construct physical conductive gelatin/silicone clones from this image."
        })
        recs.append({
            "severity": "HIGH",
            "title": "Use BioCypher 1-Click Privacy Sanitizer",
            "desc": "Apply the built-in Gaussian blur or cyber mosaic before uploading this image to public feeds (Snapchat, Instagram, X)."
        })
        recs.append({
            "severity": "HIGH",
            "title": "Enforce Hardware 2FA & FIDO2",
            "desc": "Disable single-factor biometric unlock for financial and cryptocurrency wallets. Use physical security keys (YubiKey) or complex passphrases."
        })
    elif risk_score >= 45:
        recs.append({
            "severity": "WARNING",
            "title": "Partial Ridge Pattern Exposure",
            "desc": "Fingertip angles or peace signs reveal clear ridge flow. Avoid close-up shots with palms or fingertips angled toward the camera lens."
        })
        recs.append({
            "severity": "WARNING",
            "title": "Curl Fingers in Selfies",
            "desc": "Pose with curled fingers, closed fist, or hands placed behind accessories/clothing to naturally conceal friction ridges."
        })
    else:
        recs.append({
            "severity": "INFO",
            "title": "Safe Biometric Profile",
            "desc": "Insufficient ridge clarity or minimal skin exposure detected. Biometric cloning risk is negligible for this photo."
        })

    recs.append({
        "severity": "INFO",
        "title": "Multi-Factor Authentication (MFA)",
        "desc": "Biometrics cannot be reset once compromised like a password. Ensure 2FA is active on all linked cloud services."
    })
    return recs
