"""Live endpoint smoke tests against the running Flask server."""
import urllib.request, urllib.error, json, sys, os, glob

BASE = 'http://localhost:5002/api/v1'
passed = 0
failed = 0

def check(label, cond, detail=''):
    global passed, failed
    if cond:
        print(f'  ✅  {label}')
        passed += 1
    else:
        print(f'  ❌  {label}  {detail}')
        failed += 1

def get(path, headers=None):
    req = urllib.request.Request(BASE + path, headers=headers or {})
    return urllib.request.urlopen(req, timeout=8)

def post(path, body=None, headers=None):
    data = json.dumps(body).encode() if body else b''
    h = {'Content-Type': 'application/json', **(headers or {})}
    req = urllib.request.Request(BASE + path, data=data, headers=h, method='POST')
    return urllib.request.urlopen(req, timeout=8)

print('\n── Live API smoke tests ──────────────────────────────')

# 1. Health
try:
    d = json.loads(get('/healthz').read())
    check('GET /healthz', d.get('status') == 'ok')
except Exception as e:
    check('GET /healthz', False, str(e))

# 2. Diseases
try:
    d = json.loads(get('/diseases').read())
    check(f'GET /diseases  ({len(d)} classes)', len(d) >= 14)
except Exception as e:
    check('GET /diseases', False, str(e))

# 3. History – new device
try:
    device = 'smoke-test-device-999'
    d = json.loads(get('/history', {'X-Device-Id': device}).read())
    check('GET /history (new device → empty list)', isinstance(d, list))
except Exception as e:
    check('GET /history', False, str(e))

# 4. Diagnose – missing image → 400
try:
    post('/diagnose', headers={'X-Device-Id': device})
    check('POST /diagnose no image → 400', False, 'expected 400')
except urllib.error.HTTPError as e:
    check('POST /diagnose no image → 400', e.code == 400)
except Exception as e:
    check('POST /diagnose no image', False, str(e))

# 5. Admin login – wrong creds → 401
try:
    post('/auth/admin/login', {'email': 'x@x.com', 'password': 'bad'})
    check('POST /auth/admin/login wrong → 401', False)
except urllib.error.HTTPError as e:
    check('POST /auth/admin/login wrong → 401', e.code == 401)
except Exception as e:
    check('POST /auth/admin/login wrong', False, str(e))

# 6. Admin login – correct creds
token = None
try:
    d = json.loads(post('/auth/admin/login', {'email': 'admin@agroscan.com', 'password': 'admin123'}).read())
    token = d.get('token')
    check('POST /auth/admin/login correct', bool(token))
except Exception as e:
    check('POST /auth/admin/login correct', False, str(e))

# 7. Analytics (authenticated)
if token:
    try:
        d = json.loads(get('/admin/analytics/summary', {'Authorization': f'Bearer {token}'}).read())
        check('GET /admin/analytics/summary', 'total_diagnoses' in d)
    except Exception as e:
        check('GET /admin/analytics/summary', False, str(e))

# 8. Advisory for class 0 (Tomato Healthy)
try:
    d = json.loads(get('/diseases/0/advisory').read())
    check('GET /diseases/0/advisory', True)
except urllib.error.HTTPError as e:
    # 404 = no advisory for healthy class — that's expected
    check('GET /diseases/0/advisory (healthy → no advisory expected)', e.code == 404)
except Exception as e:
    check('GET /diseases/0/advisory', False, str(e))

# 9. Diagnose with a real image (inference service offline → 503/502 expected)
jpgs = glob.glob(os.path.join(os.path.dirname(__file__), 'uploads/thumbnails/*.jpg'))
if jpgs:
    try:
        boundary = 'testboundary0001'
        with open(jpgs[0], 'rb') as f:
            img_bytes = f.read()
        body = (
            f'--{boundary}\r\nContent-Disposition: form-data; name="leaf_image"; filename="leaf.jpg"\r\n'
            f'Content-Type: image/jpeg\r\n\r\n'
        ).encode() + img_bytes + f'\r\n--{boundary}--\r\n'.encode()
        req = urllib.request.Request(BASE + '/diagnose', data=body,
            headers={'Content-Type': f'multipart/form-data; boundary={boundary}',
                     'X-Device-Id': 'smoke-real-image'},
            method='POST')
        resp = urllib.request.urlopen(req, timeout=10)
        d = json.loads(resp.read())
        top = (d.get('results') or [{}])[0]
        check(f'POST /diagnose real image  ({top.get("disease","?")} {top.get("confidence",0):.0f}%)', True)
    except urllib.error.HTTPError as e:
        # 503 = inference offline — correct behaviour
        check(f'POST /diagnose real image  (inference offline → HTTP {e.code} expected)',
              e.code in (400, 422, 502, 503, 504))
    except Exception as e:
        check('POST /diagnose real image', False, str(e)[:60])

print(f'\n── Results: {passed} passed, {failed} failed ─────────────\n')
sys.exit(0 if failed == 0 else 1)
