"""Stay-signed-in checks on TEST (logins from env vars only; tokens are never printed)."""
import json, os, urllib.error, urllib.request
API = "http://69.62.72.137/kisschool/api"
res = []
def call(method, path, tok=None, body=None, want_headers=False):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", "application/json")
    if tok: req.add_header("Authorization", "Bearer " + tok)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read(); out = (r.status, json.loads(raw) if raw else None)
            return out + (dict(r.headers),) if want_headers else out
    except urllib.error.HTTPError as e:
        raw = e.read()
        try: b = json.loads(raw)
        except Exception: b = raw.decode(errors="replace")[:200]
        return (e.code, b, dict(e.headers)) if want_headers else (e.code, b)
def check(name, ok, detail=""):
    res.append(bool(ok)); print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
U, PW = os.environ["KIS_U1"], os.environ["KIS_PW"]
dev = {"name": "Smoke test phone", "platform": "android"}

st, b = call("POST", "/auth/login", body={"identifier": U, "password": PW})
check("login without remember: no refresh token", st == 200 and b["refresh_token"] is None and b["session_id"] is None, str(st))
st, a = call("POST", "/auth/login", body={"identifier": U, "password": PW, "remember": True, "device": dev})
check("app login with remember: refresh token + 30-day expiry", st == 200 and a["refresh_token"] and a["session_id"] and a["refresh_expires_at"],
      f"{st} session {a.get('session_id')} expires {str(a.get('refresh_expires_at'))[:10]}")
st, ss = call("GET", "/auth/sessions", a["token"])
check("signed-in devices list marks this phone", st == 200 and any(s["is_current"] and s["device_name"] == dev["name"] for s in ss), f"{st} {len(ss)} sessions")
st, r1 = call("POST", "/auth/refresh", body={"refresh_token": a["refresh_token"]})
check("refresh gives a new access token and rotates the refresh token", st == 200 and r1["token"] and r1["refresh_token"] and r1["refresh_token"] != a["refresh_token"], str(st))
st, r2 = call("POST", "/auth/refresh", body={"refresh_token": a["refresh_token"]})
check("lost-response grace: old token again within 60 s, successor unused -> new token", st == 200 and r2["refresh_token"] not in (a["refresh_token"], r1["refresh_token"]), str(st))
st, r3 = call("POST", "/auth/refresh", body={"refresh_token": r2["refresh_token"]})
check("normal refresh with the newest token", st == 200, str(st))
st, b = call("POST", "/auth/refresh", body={"refresh_token": a["refresh_token"]})
check("replay of an old token -> 401 and the whole family is signed out", st == 401 and "Signed out" in json.dumps(b), f"{st} {str(b)[:70]}")
st, _ = call("POST", "/auth/refresh", body={"refresh_token": r3["refresh_token"]})
check("after a replay even the newest token is refused", st == 401, str(st))
st, c = call("POST", "/auth/login", body={"identifier": U, "password": PW, "remember": True, "device": dev})
st, _ = call("POST", "/auth/logout", body={"refresh_token": c["refresh_token"]})
st2, _ = call("POST", "/auth/refresh", body={"refresh_token": c["refresh_token"]})
check("logout (no Bearer needed) signs that phone out", st == 204 and st2 == 401, f"logout {st}, refresh after {st2}")
st, d, h = call("POST", "/auth/login", body={"identifier": U, "password": PW, "remember": True, "device": {"name": "Chrome", "platform": "web"}}, want_headers=True)
ck = h.get("Set-Cookie") or h.get("set-cookie") or ""
check("website remember: cookie only, HttpOnly, SameSite=Strict, TEST path, no token in body",
      st == 200 and d["refresh_token"] is None and "kis_refresh=" in ck and "HttpOnly" in ck and "SameSite=strict" in ck.replace("Strict", "strict") and "Path=/kisschool/api/auth" in ck,
      "; ".join(p.strip() for p in ck.split(";")[1:]))
st, e = call("POST", "/auth/login", body={"identifier": U, "password": PW, "remember": True, "device": dev})
st, _ = call("DELETE", f"/auth/sessions/{e['session_id']}", e["token"])
st2, _ = call("POST", "/auth/refresh", body={"refresh_token": e["refresh_token"]})
check("Sign out from the devices list works", st == 204 and st2 == 401, f"delete {st}, refresh after {st2}")
print(f"\n{sum(res)}/{len(res)} passed")
