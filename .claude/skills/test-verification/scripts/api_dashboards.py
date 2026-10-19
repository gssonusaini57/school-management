"""Dashboard endpoints on TEST (logins from env vars only; no names printed)."""
import json, os, urllib.error, urllib.parse, urllib.request
from datetime import date, timedelta
API = "http://69.62.72.137/kisschool/api"
CLASSES = ["Nursery", "L.K.G", "U.K.G", "1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th", "11th", "12th"]
res = []
def call(method, path, tok=None, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", "application/json")
    if tok: req.add_header("Authorization", "Bearer " + tok)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read(); return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try: return e.code, json.loads(raw)
        except Exception: return e.code, raw.decode(errors="replace")[:200]
def check(name, ok, detail=""):
    res.append(bool(ok)); print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
def login(ident):
    st, b = call("POST", "/auth/login", body={"identifier": ident, "password": os.environ["KIS_PW"]}); assert st == 200, st; return b["token"]
SUPER = login(os.environ["KIS_U1"])
st, staff = call("GET", "/staff", SUPER)
t = next(s for s in staff if s["status"] == "active" and "8th" in s["assigned_classes"] and "marks-entry" in s["allowed_menus"])
TEACHER = login(t["email"] or t["phone"])
q = lambda p, **kw: p + ("?" + urllib.parse.urlencode(kw) if kw else "")

st, cs = call("GET", "/attendance/class-summary", SUPER)
check("class-summary (super-admin): 15 classes in school order", st == 200 and [c["class_name"] for c in cs["classes"]] == CLASSES,
      f"{st} marked {cs['totals']['classes_marked']}/{cs['totals']['classes_total']} today, {cs['totals']['records']} records, {cs['totals']['percent']}%")
st, ts = call("GET", "/attendance/today-summary", SUPER)
check("today totals agree with today-summary", st == 200 and ts["total"] == cs["totals"]["records"] and ts["present"] == cs["totals"]["present"],
      f"records {cs['totals']['records']} vs {ts['total']}, present {cs['totals']['present']} vs {ts['present']}")
mine = [c for c in CLASSES if c in t["assigned_classes"]]
st, tc = call("GET", "/attendance/class-summary", TEACHER)
check("class-summary (teacher): only own classes", st == 200 and [c["class_name"] for c in tc["classes"]] == mine, f"{[c['class_name'] for c in tc['classes']]}")
first = date.today().replace(day=1).isoformat()
st, mon = call("GET", q("/attendance/class-summary", **{"from": first}), SUPER)
check("this month range works", st == 200 and mon["totals"]["records"] >= cs["totals"]["records"],
      f"{st} {mon.get('from')}..{mon.get('to')} records {mon['totals']['records']} {mon['totals']['percent']}%" if st == 200 else st)
st, b = call("GET", q("/attendance/class-summary", **{"from": (date.today() - timedelta(days=120)).isoformat()}), SUPER)
check("range over 92 days refused (422)", st == 422, f"{st} {str(b)[:80]}")
st, bs = call("GET", q("/marks/batches/summary", session="2026-27"), SUPER)
check("marks summary (super-admin)", st == 200 and "totals" in bs, f"{st} {bs.get('totals') if isinstance(bs, dict) else bs}")
st, bt = call("GET", q("/marks/batches/summary", session="2026-27"), TEACHER)
check("marks summary (teacher): own classes only", st == 200 and {i["class_name"] for i in bt["items"]} <= set(mine), f"{st} classes {sorted({i['class_name'] for i in bt['items']})}")
st, _ = call("GET", "/fees", TEACHER)
check("all-school fee list refused for a teacher (403)", st == 403, str(st))
st, _ = call("GET", "/fees", SUPER)
check("fee list still works for super-admin", st == 200, str(st))
st, tt = call("GET", "/attendance/today-summary", TEACHER)
check("today-summary scoped for the teacher", st == 200 and tt["total"] == tc["totals"]["records"], f"{tt['total']} vs {tc['totals']['records']}")
print(f"\n{sum(res)}/{len(res)} passed")
