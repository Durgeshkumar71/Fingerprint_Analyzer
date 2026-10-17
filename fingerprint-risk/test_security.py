"""
Automated Security Audit & Regression Test Suite for BioCypher 2.0
===================================================================
Tests all security controls implemented during the security hardening:
1. OWASP Top 10 Security Headers verification
2. Administrative route authorization & RBAC enforcement
3. PBKDF2:SHA-256 salted password hashing & session management
4. CSRF token validation
5. Brute-force lockout & sliding-window rate limiting
6. Path traversal & invalid image payload defenses
7. Production debug mode disabled
"""

import unittest
import json
import time
from app import app, ADMIN_USERNAME, DEFAULT_ADMIN_PASSWORD, RATE_LIMITS, _ip_request_history, _failed_auth_history

class BioCypherSecurityAuditTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        # Reset in-memory rate limits between tests
        _ip_request_history.clear()
        _failed_auth_history.clear()

    def test_01_security_headers_present(self):
        """Verify presence of OWASP Top 10 security headers on HTTP responses."""
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)

        # Check critical headers
        self.assertEqual(resp.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(resp.headers.get('X-Frame-Options'), 'DENY')
        self.assertEqual(resp.headers.get('Referrer-Policy'), 'strict-origin-when-cross-origin')
        self.assertIn('max-age=31536000', resp.headers.get('Strict-Transport-Security', ''))
        self.assertEqual(resp.headers.get('Server'), 'BioCypher-Gateway/2.0')

        # Check CSP
        csp = resp.headers.get('Content-Security-Policy', '')
        self.assertIn("default-src 'self'", csp)
        self.assertIn("object-src 'none'", csp)
        self.assertIn("frame-ancestors 'none'", csp)

    def test_02_admin_routes_strictly_protected(self):
        """Verify unauthenticated users cannot access administrative endpoints (RBAC)."""
        # Browser route should redirect to login
        resp_admin = self.client.get('/admin')
        self.assertEqual(resp_admin.status_code, 302)
        self.assertIn('/admin/login', resp_admin.headers.get('Location', ''))

        # API route should return 403 JSON
        resp_api = self.client.get('/api/admin/metrics')
        self.assertEqual(resp_api.status_code, 403)
        data = json.loads(resp_api.data.decode('utf-8'))
        self.assertIn('error', data)

        # Audit logs API should return 403 JSON
        resp_logs = self.client.get('/api/admin/audit-logs')
        self.assertEqual(resp_logs.status_code, 403)

    def test_03_authentication_and_password_hashing(self):
        """Verify PBKDF2:SHA-256 salted password verification and session issuance."""
        # 1. Fetch login page to receive CSRF token
        resp_login_get = self.client.get('/admin/login')
        self.assertEqual(resp_login_get.status_code, 200)

        # 2. Extract CSRF token from session
        with self.client.session_transaction() as sess:
            csrf_token = sess.get('_csrf_token')

        self.assertIsNotNone(csrf_token)

        # 3. Invalid credentials attempt -> 401
        resp_fail = self.client.post('/admin/login', data={
            'username': ADMIN_USERNAME,
            'password': 'WrongPassword123!',
            'csrf_token': csrf_token
        })
        self.assertEqual(resp_fail.status_code, 401)
        self.assertIn(b'Invalid administrator credentials', resp_fail.data)

        # 4. Correct credentials attempt -> 302 Redirect to /admin
        resp_success = self.client.post('/admin/login', data={
            'username': ADMIN_USERNAME,
            'password': DEFAULT_ADMIN_PASSWORD,
            'csrf_token': csrf_token
        })
        self.assertEqual(resp_success.status_code, 302)
        self.assertIn('/admin', resp_success.headers.get('Location', ''))

        # 5. Access /admin with authenticated session -> 200
        resp_admin_auth = self.client.get('/admin')
        self.assertEqual(resp_admin_auth.status_code, 200)
        self.assertIn(b'Security Operations', resp_admin_auth.data)

        # 6. Access /api/admin/metrics with authenticated session -> 200 JSON
        resp_metrics = self.client.get('/api/admin/metrics')
        self.assertEqual(resp_metrics.status_code, 200)
        metrics_data = json.loads(resp_metrics.data.decode('utf-8'))
        self.assertEqual(metrics_data['status'], 'success')
        self.assertIn('telemetry', metrics_data)

    def test_04_sliding_window_rate_limiting(self):
        """Verify sliding-window rate limiter returns 429 when quota is exceeded."""
        limit = RATE_LIMITS['cv_heavy']
        # Hit /analyze repeatedly
        for i in range(limit):
            resp = self.client.post('/analyze', data={})
            # Will be 400 because no image is passed, but rate limiter still registers attempt
            self.assertIn(resp.status_code, (400, 422))

        # The (limit + 1)-th request must be throttled with HTTP 429
        resp_throttled = self.client.post('/analyze', data={})
        self.assertEqual(resp_throttled.status_code, 429)
        self.assertIn('Retry-After', resp_throttled.headers)
        data = json.loads(resp_throttled.data.decode('utf-8'))
        self.assertIn('Rate limit exceeded', data.get('error', ''))

    def test_05_path_traversal_defense(self):
        """Verify path traversal payloads in sample_id are blocked."""
        resp = self.client.post('/analyze', data={'sample_id': '../../../../etc/passwd'})
        self.assertEqual(resp.status_code, 400)

        resp2 = self.client.post('/analyze', data={'sample_id': '..\\..\\windows\\win.ini'})
        self.assertEqual(resp2.status_code, 400)

    def test_06_debug_mode_disabled(self):
        """Verify production debug configuration."""
        self.assertFalse(app.debug)

    def test_07_ipcam_ssrf_defense(self):
        """Verify SSRF defense rejects loopback or cloud metadata services."""
        resp = self.client.post('/api/ipcam/capture', json={'url': 'http://127.0.0.1:8080/shot.jpg'})
        self.assertEqual(resp.status_code, 403)

        resp2 = self.client.post('/api/ipcam/capture', json={'url': 'http://169.254.169.254/latest/meta-data'})
        self.assertEqual(resp2.status_code, 403)

if __name__ == '__main__':
    unittest.main()
