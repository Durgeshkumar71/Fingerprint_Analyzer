/**
 * BioCypher 2.0 — Intuitive, User-Friendly Biometric Privacy Frontend
 * ===================================================================
 * Clean, accessible interaction logic for:
 * - 3-step guided scanning (Upload, Camera, Preset Examples)
 * - Plain-English biometric risk explanations
 * - Visual layer inspection with contextual explanation bar
 * - 1-Click Privacy Blur tool with safe photo download
 * - Executive forensic report dossier
 */

document.addEventListener('DOMContentLoaded', () => {
  // --- DOM Elements ---
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');
  const previewContainer = document.getElementById('previewContainer');
  const previewImg = document.getElementById('previewImg');
  const previewFilename = document.getElementById('previewFilename');
  const previewDims = document.getElementById('previewDims');
  const analyzeBtn = document.getElementById('analyzeBtn');
  const resetBtn = document.getElementById('resetBtn');

  // Input Tabs & Views
  const tabUpload = document.getElementById('tabUpload');
  const tabSamples = document.getElementById('tabSamples');
  const tabCamera = document.getElementById('tabCamera');
  const samplesView = document.getElementById('samplesView');
  const samplesGrid = document.getElementById('samplesGrid');
  const cameraView = document.getElementById('cameraView');
  const cameraFeed = document.getElementById('cameraFeed');
  const captureCameraBtn = document.getElementById('captureCameraBtn');
  const cancelCameraBtn = document.getElementById('cancelCameraBtn');

  // Loading Overlay
  const loadingOverlay = document.getElementById('loadingOverlay');
  const loadingTelemetry = document.getElementById('loadingTelemetry');

  // Results & Verdict Elements
  const resultsEmpty = document.getElementById('resultsEmpty');
  const resultsContent = document.getElementById('resultsContent');
  const verdictBanner = document.getElementById('verdictBanner');
  const riskNum = document.getElementById('riskNum');
  const riskDialCircle = document.getElementById('riskDialCircle');
  const riskLevelBadge = document.getElementById('riskLevelBadge');
  const riskVerdictExplanation = document.getElementById('riskVerdictExplanation');
  const nistBadge = document.getElementById('nistBadge');

  // Layer Inspector
  const layerImg = document.getElementById('layerImg');
  const layerButtons = document.querySelectorAll('.layer-btn');
  const layerExplanationText = document.getElementById('layerExplanationText');

  // Simplified Factors
  const mSkin = document.getElementById('mSkin');
  const bSkin = document.getElementById('bSkin');
  const mRidge = document.getElementById('mRidge');
  const bRidge = document.getElementById('bRidge');
  const mClarity = document.getElementById('mClarity');
  const bClarity = document.getElementById('bClarity');
  const mMinutiae = document.getElementById('mMinutiae');
  const bMinutiae = document.getElementById('bMinutiae');

  // Privacy Redactor Shield
  const sanitizeTriggerBtn = document.getElementById('sanitizeTriggerBtn');
  const sanitizeModeBtns = document.querySelectorAll('.friendly-mode-btn');
  const sanitizeIntensity = document.getElementById('sanitizeIntensity');
  const intensityVal = document.getElementById('intensityVal');
  const sanitizedPreviewWrap = document.getElementById('sanitizedPreviewWrap');
  const sanitizedImg = document.getElementById('sanitizedImg');
  const sanitizedStatusBadge = document.getElementById('sanitizedStatusBadge');
  const downloadSafeBtn = document.getElementById('downloadSafeBtn');

  // Recommendations & Modal
  const recsList = document.getElementById('recsList');
  const openReportBtn = document.getElementById('openReportBtn');
  const reportModalBackdrop = document.getElementById('reportModalBackdrop');
  const closeReportBtn = document.getElementById('closeReportBtn');
  const printReportBtn = document.getElementById('printReportBtn');
  const reportContent = document.getElementById('reportContent');

  // --- State Variables ---
  let selectedFile = null;
  let selectedBase64 = null;
  let activeSampleId = null;
  let currentLayers = null;
  let activeAnalysisData = null;
  let cameraStream = null;
  let activeSanitizeMode = 'blur';

  // --- Layer Explanations Mapping ---
  const LAYER_EXPLANATIONS = {
    composite_hud: "Overview: Showing detected finger regions with tactical focus brackets.",
    gabor_heatmap: "Ridge Heatmap: Yellow and bright areas reveal intense friction ridge patterns.",
    minutiae_map: "Minutiae Skeleton: Green lines trace ridges. Cyan circles are ridge endings, magenta diamonds are ridge forks.",
    skin_mask: "Hand Area: Highlighted contours show where human skin and hands were detected.",
    original: "Original Photo: The raw picture before biometric processing."
  };

  // --- Input Tab Switching ---
  function switchInputTab(mode) {
    tabUpload.classList.remove('active');
    tabSamples.classList.remove('active');
    tabCamera.classList.remove('active');

    dropZone.style.display = 'none';
    samplesView.classList.remove('active');
    cameraView.classList.remove('active');

    stopCamera();

    if (mode === 'upload') {
      tabUpload.classList.add('active');
      if (!selectedFile && !selectedBase64 && !activeSampleId) {
        dropZone.style.display = 'flex';
      } else {
        previewContainer.style.display = 'flex';
      }
    } else if (mode === 'samples') {
      tabSamples.classList.add('active');
      samplesView.classList.add('active');
      loadSamplesList();
    } else if (mode === 'camera') {
      tabCamera.classList.add('active');
      cameraView.classList.add('active');
      startCamera();
    }
  }

  tabUpload.addEventListener('click', () => switchInputTab('upload'));
  tabSamples.addEventListener('click', () => switchInputTab('samples'));
  tabCamera.addEventListener('click', () => switchInputTab('camera'));

  // --- File Dropzone & Input ---
  function handleFileSelected(file) {
    if (!file) return;
    selectedFile = file;
    selectedBase64 = null;
    activeSampleId = null;

    const reader = new FileReader();
    reader.onload = e => {
      previewImg.src = e.target.result;
      previewFilename.textContent = file.name;
      previewDims.textContent = `${(file.size / 1024).toFixed(1)} KB — Ready to scan`;

      dropZone.style.display = 'none';
      samplesView.classList.remove('active');
      cameraView.classList.remove('active');
      previewContainer.style.display = 'flex';
    };
    reader.readAsDataURL(file);
  }

  fileInput.addEventListener('change', e => {
    if (e.target.files[0]) handleFileSelected(e.target.files[0]);
  });

  dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
  });

  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    if (e.dataTransfer.files[0]) handleFileSelected(e.dataTransfer.files[0]);
  });

  // --- Live WebRTC Camera ---
  async function startCamera() {
    try {
      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        cameraStream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 }, facingMode: 'user' }
        });
        cameraFeed.srcObject = cameraStream;
        await cameraFeed.play();
      } else {
        alert('Camera access is not supported by your current browser.');
      }
    } catch (err) {
      console.warn('Camera error:', err);
      alert('Unable to access camera. Please check camera permissions or upload a file.');
      switchInputTab('upload');
    }
  }

  function stopCamera() {
    if (cameraStream) {
      cameraStream.getTracks().forEach(track => track.stop());
      cameraStream = null;
    }
  }

  captureCameraBtn.addEventListener('click', () => {
    const canvas = document.createElement('canvas');
    canvas.width = cameraFeed.videoWidth || 640;
    canvas.height = cameraFeed.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(cameraFeed, 0, 0, canvas.width, canvas.height);

    const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
    selectedBase64 = dataUrl;
    selectedFile = null;
    activeSampleId = null;

    stopCamera();
    cameraView.classList.remove('active');
    previewImg.src = dataUrl;
    previewFilename.textContent = 'Camera Snapshot';
    previewDims.textContent = `${canvas.width}x${canvas.height}px — Ready to scan`;
    previewContainer.style.display = 'flex';
  });

  cancelCameraBtn.addEventListener('click', () => {
    stopCamera();
    switchInputTab('upload');
  });

  // --- Benchmark Presets Gallery ---
  async function loadSamplesList() {
    try {
      const resp = await fetch('/api/samples');
      const data = await resp.json();
      if (data.status === 'success' && data.samples) {
        renderSamplesGrid(data.samples);
      }
    } catch (err) {
      console.error('Failed to load sample presets:', err);
    }
  }

  function getSampleEmoji(id) {
    if (id === 'peace_sign') return '✌️';
    if (id === 'macro_finger') return '🔍';
    if (id === 'safe_fist') return '✊';
    return '🏃';
  }

  function renderSamplesGrid(samples) {
    samplesGrid.innerHTML = '';
    samples.forEach(s => {
      const card = document.createElement('div');
      card.className = 'preset-option-card';
      if (activeSampleId === s.id) card.classList.add('active');

      const isHighRisk = s.risk_expectation.includes('CRITICAL') || s.risk_expectation.includes('HIGH');
      const riskClass = isHighRisk ? 'badge-risk-CRITICAL' : 'badge-risk-SAFE';
      const riskLabel = isHighRisk ? 'High Risk Example' : 'Safe Pose Example';
      const emoji = getSampleEmoji(s.id);

      card.innerHTML = `
        <div class="preset-card-top">
          <span class="preset-emoji">${emoji}</span>
          <span class="preset-risk-badge ${riskClass}">${riskLabel}</span>
        </div>
        <h5>${s.title}</h5>
        <p>${s.description}</p>
      `;

      card.addEventListener('click', () => {
        activeSampleId = s.id;
        selectedFile = null;
        selectedBase64 = null;

        document.querySelectorAll('.preset-option-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');

        previewImg.src = `/static/samples/${s.filename}`;
        previewFilename.textContent = s.title;
        previewDims.textContent = `${s.category} — Click scan below`;

        samplesView.classList.remove('active');
        previewContainer.style.display = 'flex';
      });

      samplesGrid.appendChild(card);
    });
  }

  // --- Reset Selection ---
  resetBtn.addEventListener('click', () => {
    selectedFile = null;
    selectedBase64 = null;
    activeSampleId = null;
    fileInput.value = '';
    previewContainer.style.display = 'none';
    resultsEmpty.style.display = 'flex';
    resultsContent.classList.remove('active');
    sanitizedPreviewWrap.classList.remove('active');
    downloadSafeBtn.style.display = 'none';
    switchInputTab('upload');
  });

  // --- Analysis Trigger ---
  analyzeBtn.addEventListener('click', async () => {
    if (!selectedFile && !selectedBase64 && !activeSampleId) return;

    loadingOverlay.classList.add('active');
    analyzeBtn.disabled = true;

    // Friendly sequential progress messages
    const steps = [
      'Detecting hand and finger regions...',
      'Applying Gabor filters to isolate fingerprint ridges...',
      'Mapping ridge endings and bifurcation keypoints...',
      'Calculating cloning risk and defense recommendations...'
    ];
    let stepIdx = 0;
    const interval = setInterval(() => {
      stepIdx = (stepIdx + 1) % steps.length;
      loadingTelemetry.textContent = steps[stepIdx];
    }, 450);

    try {
      let resp;
      if (activeSampleId) {
        resp = await fetch('/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sample_id: activeSampleId })
        });
      } else if (selectedBase64) {
        resp = await fetch('/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image_b64: selectedBase64 })
        });
      } else if (selectedFile) {
        const formData = new FormData();
        formData.append('image', selectedFile);
        resp = await fetch('/analyze', {
          method: 'POST',
          body: formData
        });
      }

      const data = await resp.json();
      clearInterval(interval);

      if (data.error) {
        alert('Scan Error: ' + data.error);
        return;
      }

      displayResults(data);
    } catch (err) {
      clearInterval(interval);
      console.error('Scan failed:', err);
      alert('Unable to complete scan. Please ensure the server is running.');
    } finally {
      loadingOverlay.classList.remove('active');
      analyzeBtn.disabled = false;
    }
  });

  // --- Render Results ---
  function displayResults(data) {
    activeAnalysisData = data;
    currentLayers = data.layers;

    resultsEmpty.style.display = 'none';
    resultsContent.classList.add('active');

    // 1. Verdict Banner & Explanation
    animateNumber('riskNum', data.risk_score);
    verdictBanner.className = `verdict-banner verdict-${data.risk_level}`;
    riskDialCircle.style.borderColor = data.risk_color;
    riskNum.style.color = data.risk_color;

    let friendlyTitle = '';
    let friendlyExplanation = '';

    if (data.risk_score >= 70) {
      friendlyTitle = '⚠️ Critical Fingerprint Exposure!';
      friendlyExplanation = 'Your fingertips are in sharp focus and close to the camera. An attacker could easily extract your ridge patterns and create a fake biometric replica. We recommend applying the privacy blur below before sharing this photo.';
      nistBadge.textContent = 'HIGH RISK PHOTO';
      nistBadge.style.color = 'var(--rose)';
    } else if (data.risk_score >= 45) {
      friendlyTitle = '⚠️ High Biometric Exposure Risk';
      friendlyExplanation = 'Fingerprint ridge lines are clearly visible on your fingers. To be safe, use the 1-click blur tool below to conceal your ridges before posting.';
      nistBadge.textContent = 'ATTENTION NEEDED';
      nistBadge.style.color = 'var(--amber)';
    } else if (data.risk_score >= 25) {
      friendlyTitle = '🟡 Moderate Exposure Risk';
      friendlyExplanation = 'Some finger skin is visible, but the ridge detail is only partially resolved. Cloned extraction would be difficult from this photo.';
      nistBadge.textContent = 'MODERATE';
      nistBadge.style.color = 'var(--amber)';
    } else {
      friendlyTitle = '✅ Safe Photo — Low Exposure Risk';
      friendlyExplanation = 'Your fingers are either curled, placed at a safe distance, or hidden from the camera. Fingerprint cloning is not feasible from this picture!';
      nistBadge.textContent = 'SAFE PHOTO';
      nistBadge.style.color = 'var(--emerald)';
    }

    riskLevelBadge.textContent = friendlyTitle;
    riskVerdictExplanation.textContent = friendlyExplanation;

    // 2. Default Visual Layer
    updateActiveLayerTab('composite_hud');
    renderLayerImage('composite_hud');

    // 3. Simplified Metric Bars
    animateMetricBar('mSkin', 'bSkin', data.metrics.skin_detected);
    animateMetricBar('mRidge', 'bRidge', data.metrics.ridge_visibility);
    animateMetricBar('mClarity', 'bClarity', data.metrics.image_clarity);
    animateMetricBar('mMinutiae', 'bMinutiae', Math.min((data.metrics.minutiae_count / 20) * 100, 100), `${data.metrics.minutiae_count} points`);

    // 4. Actionable Defense Recommendations
    recsList.innerHTML = '';
    data.recommendations.forEach(rec => {
      const card = document.createElement('div');
      card.style.background = 'var(--bg-surface)';
      card.style.border = '1px solid var(--border-card)';
      card.style.borderRadius = 'var(--radius-sm)';
      card.style.padding = '10px 14px';

      const titleP = document.createElement('div');
      titleP.style.fontWeight = '700';
      titleP.style.fontSize = '0.82rem';
      titleP.style.color = '#fff';
      titleP.style.marginBottom = '2px';
      titleP.textContent = `▸ ${rec.title}`;

      const descP = document.createElement('div');
      descP.style.fontSize = '0.75rem';
      descP.style.color = 'var(--text-secondary)';
      descP.style.lineHeight = '1.4';
      descP.textContent = rec.desc;

      card.appendChild(titleP);
      card.appendChild(descP);
      recsList.appendChild(card);
    });

    // Reset Sanitizer Preview
    sanitizedPreviewWrap.classList.remove('active');
    downloadSafeBtn.style.display = 'none';
  }

  // --- Layer Inspector Switching ---
  function updateActiveLayerTab(layerKey) {
    layerButtons.forEach(btn => {
      if (btn.getAttribute('data-layer') === layerKey) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }

  function renderLayerImage(layerKey) {
    if (!currentLayers || !currentLayers[layerKey]) return;
    layerImg.src = 'data:image/jpeg;base64,' + currentLayers[layerKey];
    layerExplanationText.textContent = LAYER_EXPLANATIONS[layerKey] || "Inspection layer active.";
  }

  layerButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const layerKey = btn.getAttribute('data-layer');
      updateActiveLayerTab(layerKey);
      renderLayerImage(layerKey);
    });
  });

  // --- Privacy Shield (1-Click Blur Tool) ---
  sanitizeModeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      sanitizeModeBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeSanitizeMode = btn.getAttribute('data-mode');
    });
  });

  sanitizeIntensity.addEventListener('input', e => {
    intensityVal.textContent = e.target.value;
  });

  sanitizeTriggerBtn.addEventListener('click', async () => {
    if (!activeAnalysisData) return;
    sanitizeTriggerBtn.disabled = true;
    sanitizeTriggerBtn.textContent = 'Applying Privacy Blur...';

    const intensity = sanitizeIntensity.value;

    try {
      let resp;
      if (activeSampleId) {
        resp = await fetch('/sanitize', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sample_id: activeSampleId, mode: activeSanitizeMode, intensity })
        });
      } else if (selectedBase64) {
        resp = await fetch('/sanitize', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image_b64: selectedBase64, mode: activeSanitizeMode, intensity })
        });
      } else if (selectedFile) {
        const formData = new FormData();
        formData.append('image', selectedFile);
        formData.append('mode', activeSanitizeMode);
        formData.append('intensity', intensity);
        resp = await fetch('/sanitize', {
          method: 'POST',
          body: formData
        });
      }

      const result = await resp.json();
      if (result.error) {
        alert('Privacy Filter Error: ' + result.error);
        return;
      }

      // Display Sanitized Result
      const dataUri = 'data:image/jpeg;base64,' + result.sanitized_image;
      sanitizedImg.src = dataUri;
      sanitizedPreviewWrap.classList.add('active');

      sanitizedStatusBadge.innerHTML = `
        <span>🛡️ Fingerprints Protected!</span>
        <span>•</span>
        <span>Post-Exposure Risk: <strong>${result.post_risk_score}% (${result.post_risk_level})</strong></span>
        <span>•</span>
        <span>Safe to post on Instagram, Snapchat & TikTok!</span>
      `;

      downloadSafeBtn.style.display = 'inline-flex';
      downloadSafeBtn.href = dataUri;
      downloadSafeBtn.download = `biocypher_safe_${Date.now()}.jpg`;

    } catch (err) {
      console.error('Sanitization failed:', err);
      alert('Unable to apply privacy blur.');
    } finally {
      sanitizeTriggerBtn.disabled = false;
      sanitizeTriggerBtn.textContent = '⚡ Apply Privacy Filter';
    }
  });

  // --- Executive Audit Dossier Modal ---
  openReportBtn.addEventListener('click', () => {
    if (!activeAnalysisData) {
      alert('Please scan an image first to generate an audit report.');
      return;
    }
    generateReportHtml(activeAnalysisData);
    reportModalBackdrop.classList.add('open');
  });

  closeReportBtn.addEventListener('click', () => {
    reportModalBackdrop.classList.remove('open');
  });

  reportModalBackdrop.addEventListener('click', e => {
    if (e.target === reportModalBackdrop) {
      reportModalBackdrop.classList.remove('open');
    }
  });

  printReportBtn.addEventListener('click', () => {
    window.print();
  });

  function escapeHtml(str) {
    if (str === null || str === undefined) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function generateReportHtml(data) {
    const timestamp = escapeHtml(new Date().toUTCString());
    const safeFilename = escapeHtml(data.filename);
    const safeResolution = escapeHtml(data.resolution);
    const safeRiskLevel = escapeHtml(data.risk_level);
    const safeRiskScore = Number(data.risk_score) || 0;

    reportContent.innerHTML = `
      <div style="text-align:center;margin-bottom:20px;">
        <h4 style="font-family:var(--font-heading);color:var(--sky-blue);font-size:1.3rem;">Biometric Privacy Audit Report</h4>
        <p style="font-size:0.8rem;color:var(--text-secondary);">Summary of fingerprint exposure and extractability metrics</p>
      </div>

      <div style="background:var(--bg-surface);padding:14px;border-radius:var(--radius-sm);margin-bottom:16px;">
        <div style="display:flex;justify-content:space-between;font-size:0.82rem;margin-bottom:6px;">
          <span>Target File:</span>
          <strong>${safeFilename} (${safeResolution})</strong>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:0.82rem;margin-bottom:6px;">
          <span>Overall Risk:</span>
          <strong style="color:${data.risk_color}">${safeRiskLevel} (${safeRiskScore}/100)</strong>
        </div>
        <div style="display:flex;justify-content:space-between;font-size:0.82rem;">
          <span>Generated On:</span>
          <span>${timestamp}</span>
        </div>
      </div>

      <h5 style="font-size:0.88rem;color:#fff;margin:14px 0 8px;">Key Biometric Observations:</h5>
      <ul style="font-size:0.8rem;color:var(--text-secondary);display:flex;flex-direction:column;gap:6px;padding-left:18px;">
        <li>Finger skin detected in frame: <strong>${Number(data.metrics.skin_detected).toFixed(1)}%</strong></li>
        <li>Directional ridge visibility: <strong>${Number(data.metrics.ridge_visibility).toFixed(1)}%</strong></li>
        <li>Image clarity / sharpness: <strong>${Number(data.metrics.image_clarity).toFixed(1)}%</strong></li>
        <li>Admissible minutiae keypoints: <strong>${Number(data.metrics.minutiae_count)} points</strong></li>
      </ul>

      <h5 style="font-size:0.88rem;color:#fff;margin:14px 0 8px;">Recommended Safeguards:</h5>
      <ul style="font-size:0.8rem;color:var(--text-secondary);display:flex;flex-direction:column;gap:6px;padding-left:18px;">
        ${data.recommendations.map(r => `<li><strong>${escapeHtml(r.title)}:</strong> ${escapeHtml(r.desc)}</li>`).join('')}
      </ul>
    `;
  }

  // --- Animation Helpers ---
  function animateNumber(elementId, targetValue) {
    const el = document.getElementById(elementId);
    let current = 0;
    const duration = 700;
    const stepTime = 20;
    const stepCount = duration / stepTime;
    const increment = targetValue / stepCount;

    const timer = setInterval(() => {
      current += increment;
      if (current >= targetValue) {
        current = targetValue;
        clearInterval(timer);
      }
      el.textContent = Math.round(current);
    }, stepTime);
  }

  function animateMetricBar(labelId, barId, value, customText = null) {
    document.getElementById(labelId).textContent = customText || `${value.toFixed(1)}%`;
    setTimeout(() => {
      document.getElementById(barId).style.width = Math.min(Math.max(value, 0), 100) + '%';
    }, 120);
  }
});
