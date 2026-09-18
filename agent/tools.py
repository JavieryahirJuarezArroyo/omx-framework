"""Cliente del bridge OMX (HTTP). Reusable para varios robots/casos."""
import json
import urllib.request
import urllib.error

BRIDGE = 'http://localhost:8000'
LIMITS = {
    'joint1': (-4.71, 6.28),
    'joint2': (-2.09, 1.57),
    'joint3': (-2.09, 1.57),
    'joint4': (-1.74, 1.74),
    'joint5': (-4.71, 4.71),
}
NAMES = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5']


def _req(method, path, body=None, timeout=30):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BRIDGE + path, data=data, method=method,
                               headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(r, timeout=timeout) as f:
            return json.loads(f.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:300]
        raise RuntimeError(f'{path} -> HTTP {e.code}: {detail}')


def get_state():
    return _req('GET', '/state', timeout=10)


def health():
    return _req('GET', '/health', timeout=5)


def move_joints(q, seconds=4.0):
    return _req('POST', '/move_joints', {'joints': list(q), 'seconds': seconds},
                timeout=seconds + 25)


def home():
    return _req('POST', '/home', timeout=30)


def init():
    return _req('POST', '/init', timeout=30)


def gripper(open01, seconds=2.0):
    return _req('POST', '/gripper', {'open': open01, 'seconds': seconds}, timeout=20)


def validate(q):
    bad = []
    for n, v in zip(NAMES, q):
        lo, hi = LIMITS[n]
        if not (lo <= v <= hi):
            bad.append(f'{n}={v} fuera de [{lo},{hi}]')
    return bad
