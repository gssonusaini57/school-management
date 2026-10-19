"""Device sessions: "stay signed in" through rotated refresh tokens (migration 0021).

Android gets the refresh token in the login body, the web in an HttpOnly cookie;
POST /auth/refresh rotates it, heals a lost response inside 60 s and kills the
whole family on a replay; credential changes revoke the account's sessions.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
from types import SimpleNamespace

import jwt
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from app.config import settings
from app.deps import _parse
from app.main import app
from app.models.device_session import DeviceSession, SessionAccountType, SessionVia
from app.models.password_reset import PasswordResetToken, ResetAccountType
from app.models.record_status import RecordStatus
from app.routers.auth import ADMIN_EMAIL, SUPER_ADMIN_EMAIL, SIGNED_OUT_MSG, TOO_MANY_ATTEMPTS_MSG
from app.security import create_token, decode_token

from .conftest import auth
from .factories import staff
from .test_migration_0016 import _load

ADMIN_PW = settings.ADMIN_DEFAULT_PASSWORD
SUPER_PW = settings.SUPER_ADMIN_DEFAULT_PASSWORD
TEACHER_EMAIL = "gurpreet@kisschool.in"
COOKIE = settings.AUTH_COOKIE_NAME


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def login(client, identifier, password, *, remember=False, platform="android", name="Pixel 7"):
    body = {"identifier": identifier, "password": password}
    if remember:
        body.update(remember=True, device={"name": name, "platform": platform})
    return client.post("/api/auth/login", json=body)


def refresh(client, raw=None):
    """Body token (Android) when given, otherwise whatever cookie the client holds (web)."""
    return client.post("/api/auth/refresh", json={"refresh_token": raw} if raw else None)


def bearer(body: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {body['token']}"}


def cookie_of(response) -> SimpleCookie:
    jar = SimpleCookie()
    jar.load(response.headers["set-cookie"])
    return jar


def rows(db) -> list[DeviceSession]:
    db.expire_all()
    return db.query(DeviceSession).order_by(DeviceSession.id).all()


def by_id(db) -> dict[int, DeviceSession]:
    return {r.id: r for r in rows(db)}


def sha(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


@pytest.fixture()
def teacher(db):
    t = staff(db, name="Gurpreet Kaur", email=TEACHER_EMAIL, phone="9876543210", password="pw", classes=["8th"])
    db.commit()
    return t


# --- login -----------------------------------------------------------------------

def test_login_without_remember_opens_no_session(client, db, teacher):
    r = login(client, TEACHER_EMAIL, "pw")
    assert r.status_code == 200
    body = r.json()
    assert body["token"] and body["role"] == "staff" and body["allowed_classes"] == ["8th"]
    assert body["session_id"] is None and body["refresh_token"] is None and body["refresh_expires_at"] is None
    assert "set-cookie" not in r.headers
    assert "sid" not in decode_token(body["token"])
    assert rows(db) == []


def test_android_remember_returns_a_refresh_token_in_the_body(client, db, teacher):
    r = login(client, TEACHER_EMAIL, "pw", remember=True, platform="android", name="Pixel 7")
    assert r.status_code == 200
    body = r.json()
    (row,) = rows(db)
    assert body["session_id"] == row.id and decode_token(body["token"])["sid"] == row.id
    assert sha(body["refresh_token"]) == row.token_hash
    assert datetime.fromisoformat(body["refresh_expires_at"]) == row.expires_at
    assert "set-cookie" not in r.headers
    assert (row.account_type, row.account_ref, row.via, row.platform.value, row.device_name) == (
        SessionAccountType.staff, str(teacher.id), SessionVia.password, "android", "Pixel 7")
    assert len(row.family_id) == 32 and len(row.token_hash) == 64
    assert row.rotated_at is None and row.revoked_at is None and row.last_used_at is None
    now = utcnow()
    assert timedelta(days=30, minutes=-1) < row.expires_at - now <= timedelta(days=30)
    assert timedelta(days=180, minutes=-1) < row.absolute_expires_at - now <= timedelta(days=180)
    assert row.created_at is not None and row.ip and row.user_agent


def test_web_remember_sets_an_httponly_cookie_and_no_body_token(client, db, teacher):
    r = login(client, TEACHER_EMAIL, "pw", remember=True, platform="web", name="Chrome on Mac")
    assert r.status_code == 200
    body = r.json()
    (row,) = rows(db)
    assert body["session_id"] == row.id and body["refresh_token"] is None and body["refresh_expires_at"] is None
    assert row.platform.value == "web" and row.device_name == "Chrome on Mac"
    header = r.headers["set-cookie"]
    morsel = cookie_of(r)[COOKIE]
    assert sha(morsel.value) == row.token_hash
    assert morsel["httponly"] and morsel["samesite"] == "Strict" and morsel["path"] == "/api/auth"
    assert morsel["max-age"] == str(30 * 86400)
    assert "SameSite=Strict" in header and "Secure" not in header     # plain http: no Secure
    # Over HTTPS the cookie is also Secure.
    https = TestClient(app, base_url="https://testserver")
    r2 = login(https, TEACHER_EMAIL, "pw", remember=True, platform="web")
    assert r2.status_code == 200 and "; Secure" in r2.headers["set-cookie"]


def test_remember_without_device_defaults_to_the_web_cookie(client, db, teacher):
    r = client.post("/api/auth/login", json={"identifier": TEACHER_EMAIL, "password": "pw", "remember": True})
    assert r.status_code == 200 and r.json()["refresh_token"] is None and COOKIE in r.headers["set-cookie"]
    assert rows(db)[0].device_name == ""


def test_admin_and_super_admin_sessions_are_filed_under_their_jwt_subjects(client, db):
    a = login(client, ADMIN_EMAIL, ADMIN_PW, remember=True).json()
    s = login(client, SUPER_ADMIN_EMAIL, SUPER_PW, remember=True).json()
    assert (a["role"], a["name"], s["role"], s["name"]) == ("admin", "Administrator", "super_admin", "Super Admin")
    ra, rs = rows(db)
    assert (ra.account_type, ra.account_ref) == (SessionAccountType.admin, "admin")
    assert (rs.account_type, rs.account_ref) == (SessionAccountType.super_admin, "superadmin")
    assert decode_token(refresh(client, s["refresh_token"]).json()["token"])["sub"] == "superadmin"


# --- refresh ---------------------------------------------------------------------

def test_refresh_rotates_the_token_and_rebuilds_claims(client, db, teacher):
    raw1 = login(client, TEACHER_EMAIL, "pw", remember=True).json()["refresh_token"]
    (old,) = rows(db)
    old.expires_at = utcnow() + timedelta(days=10)          # as if last used 20 days ago
    db.commit()
    # An admin edits the teacher's classes and menus: the session is untouched...
    r = client.patch(f"/api/staff/{teacher.id}",
                     json={"assigned_classes": ["7th", "8th"], "allowed_menus": ["dashboard", "attendance"]},
                     headers=auth("admin"))
    assert r.status_code == 200
    r = refresh(client, raw1)
    assert r.status_code == 200
    body = r.json()
    # ...and the refreshed token carries the new scope.
    claims = decode_token(body["token"])
    assert claims["allowed_classes"] == ["7th", "8th"] and claims["allowed_menus"] == ["dashboard", "attendance"]
    assert body["allowed_classes"] == ["7th", "8th"] and body["allowed_menus"] == ["dashboard", "attendance"]
    assert (body["role"], body["name"], body["force_password_change"]) == ("staff", "Gurpreet Kaur", False)
    old, new = rows(db)
    assert body["session_id"] == new.id == claims["sid"] and body["refresh_token"] != raw1
    assert sha(body["refresh_token"]) == new.token_hash
    assert datetime.fromisoformat(body["refresh_expires_at"]) == new.expires_at
    assert old.rotated_at is not None and old.replaced_by_id == new.id and old.revoked_reason == "rotated"
    assert old.revoked_at is None and old.last_used_at is not None
    assert new.family_id == old.family_id and new.absolute_expires_at == old.absolute_expires_at
    assert new.expires_at > old.expires_at + timedelta(days=19) and new.last_used_at is None
    assert (new.via, new.platform, new.device_name) == (old.via, old.platform, "Pixel 7")
    assert client.get("/api/auth/me", headers=bearer(body)).json()["allowed_classes"] == ["7th", "8th"]


def test_refresh_reports_the_absolute_cap_when_it_is_the_nearer_expiry(client, db, teacher):
    raw = login(client, TEACHER_EMAIL, "pw", remember=True).json()["refresh_token"]
    (row,) = rows(db)
    row.absolute_expires_at = utcnow() + timedelta(days=5)
    db.commit()
    r = refresh(client, raw)
    assert r.status_code == 200
    assert datetime.fromisoformat(r.json()["refresh_expires_at"]) == row.absolute_expires_at


def test_web_refresh_rotates_the_cookie(client, db, teacher):
    r = login(client, TEACHER_EMAIL, "pw", remember=True, platform="web")
    raw1 = cookie_of(r)[COOKIE].value
    r = refresh(client)                                       # cookie only: no body, no Bearer
    assert r.status_code == 200 and r.json()["refresh_token"] is None
    raw2 = cookie_of(r)[COOKIE].value
    assert raw2 != raw1 and sha(raw2) == rows(db)[1].token_hash
    header = r.headers["set-cookie"]
    assert "HttpOnly" in header and "SameSite=Strict" in header and "Path=/api/auth" in header
    assert f"Max-Age={30 * 86400}" in header
    assert r.json()["session_id"] == rows(db)[1].id
    assert refresh(client).status_code == 200                 # the browser now holds raw2
    # A dead cookie coming back is a replay: 401 and the response expires the cookie.
    r = TestClient(app).post("/api/auth/refresh", headers={"Cookie": f"{COOKIE}={raw1}"})
    assert r.status_code == 401 and r.json() == {"detail": SIGNED_OUT_MSG}
    assert "Max-Age=0" in r.headers["set-cookie"] and "Path=/api/auth" in r.headers["set-cookie"]


def test_refresh_without_any_token_is_401(client):
    r = refresh(client)
    assert r.status_code == 401 and r.json() == {"detail": SIGNED_OUT_MSG}
    assert refresh(client, "not-a-token").status_code == 401


def test_replaying_a_consumed_token_kills_the_whole_family(client, db, teacher):
    raw1 = login(client, TEACHER_EMAIL, "pw", remember=True).json()["refresh_token"]
    raw2 = refresh(client, raw1).json()["refresh_token"]
    raw3 = refresh(client, raw2).json()["refresh_token"]     # raw2's row is used: no grace left for raw1
    r = refresh(client, raw1)
    assert r.status_code == 401 and r.json() == {"detail": SIGNED_OUT_MSG}
    family = rows(db)
    assert len(family) == 3 and len({f.family_id for f in family}) == 1
    assert all(f.revoked_at is not None and f.revoked_reason == "replay" for f in family)
    assert refresh(client, raw3).status_code == 401


def test_a_rotated_token_outside_the_grace_window_is_a_replay(client, db, teacher):
    raw1 = login(client, TEACHER_EMAIL, "pw", remember=True).json()["refresh_token"]
    assert refresh(client, raw1).status_code == 200
    old, new = rows(db)
    old.rotated_at = utcnow() - timedelta(seconds=61)
    db.commit()
    assert refresh(client, raw1).status_code == 401
    old, new = rows(db)
    assert (old.revoked_reason, new.revoked_reason) == ("replay", "replay")


def test_lost_response_grace_reissues_within_60_seconds(client, db, teacher):
    raw1 = login(client, TEACHER_EMAIL, "pw", remember=True).json()["refresh_token"]
    raw2 = refresh(client, raw1).json()["refresh_token"]     # response lost: the device never stored raw2
    r = refresh(client, raw1)                                 # so it retries with raw1
    assert r.status_code == 200
    raw3 = r.json()["refresh_token"]
    assert raw3 not in (raw1, raw2)
    row1, row2, row3 = rows(db)
    assert row2.revoked_reason == "superseded" and row2.revoked_at is not None
    assert row1.replaced_by_id == row3.id and row1.revoked_reason == "rotated" and row1.revoked_at is None
    assert row3.family_id == row1.family_id and row3.revoked_at is None and r.json()["session_id"] == row3.id
    assert row3.absolute_expires_at == row1.absolute_expires_at
    assert refresh(client, raw2).status_code == 401          # the superseded token is dead
    assert refresh(client, raw3).status_code == 200          # the device carries on with raw3


def test_sliding_and_absolute_expiry(client, db, teacher):
    raw = login(client, TEACHER_EMAIL, "pw", remember=True).json()["refresh_token"]
    (row,) = rows(db)
    row.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    r = refresh(client, raw)
    assert r.status_code == 401 and r.json() == {"detail": SIGNED_OUT_MSG}
    row.expires_at = utcnow() + timedelta(days=30)
    row.absolute_expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    assert refresh(client, raw).status_code == 401
    row.absolute_expires_at = utcnow() + timedelta(days=1)
    db.commit()
    assert refresh(client, raw).status_code == 200


def test_a_deleted_teacher_cannot_refresh_but_pending_delete_can(client, db, teacher):
    a = login(client, TEACHER_EMAIL, "pw", remember=True).json()
    teacher.status = RecordStatus.deleted
    db.commit()
    r = refresh(client, a["refresh_token"])
    assert r.status_code == 401 and r.json()["detail"] == SIGNED_OUT_MSG
    assert rows(db)[0].revoked_reason == "account_deleted"
    teacher.status = RecordStatus.pending_delete
    db.commit()
    b = login(client, TEACHER_EMAIL, "pw", remember=True).json()
    assert refresh(client, b["refresh_token"]).status_code == 200


def test_temp_password_sessions_die_when_the_temp_password_is_cleared(client, db):
    t = staff(db, email=TEACHER_EMAIL, password="pw", temp_password="cover123", force_password_change=True)
    db.commit()
    via_temp = login(client, TEACHER_EMAIL, "cover123", remember=True, name="Office PC").json()
    via_pw = login(client, TEACHER_EMAIL, "pw", remember=True, name="Pixel 7").json()
    # A temp login is never "must change password"; the teacher's own is (flag set above).
    assert via_temp["force_password_change"] is False and via_pw["force_password_change"] is True
    temp_row, pw_row = rows(db)
    assert (temp_row.via, pw_row.via) == (SessionVia.temp_password, SessionVia.password)
    r = refresh(client, via_temp["refresh_token"])
    assert r.status_code == 200 and r.json()["force_password_change"] is False
    raw_temp = r.json()["refresh_token"]
    assert client.delete(f"/api/staff/{t.id}/temp-password", headers=auth("admin")).status_code == 200
    assert refresh(client, raw_temp).status_code == 401
    r = refresh(client, via_pw["refresh_token"])
    assert r.status_code == 200 and r.json()["force_password_change"] is True
    reasons = {row.id: row.revoked_reason for row in rows(db)}
    assert reasons[temp_row.id] == "temp_password_cleared" and reasons[r.json()["session_id"]] is None
    assert all(row.revoked_reason == "temp_password_cleared" for row in rows(db) if row.via == SessionVia.temp_password)


def test_refresh_refuses_a_temp_session_once_the_hash_is_gone_even_without_the_hook(client, db):
    t = staff(db, email=TEACHER_EMAIL, temp_password="cover123")
    db.commit()
    raw = login(client, TEACHER_EMAIL, "cover123", remember=True).json()["refresh_token"]
    t.temp_password_hash = None
    db.commit()
    assert refresh(client, raw).status_code == 401
    assert rows(db)[0].revoked_reason == "temp_password_cleared"


# --- revocation hooks ------------------------------------------------------------

def test_admin_password_change_signs_the_other_devices_out(client, db):
    a = login(client, ADMIN_EMAIL, ADMIN_PW, remember=True, name="Laptop").json()
    b = login(client, ADMIN_EMAIL, ADMIN_PW, remember=True, name="Phone").json()
    r = client.post("/api/auth/change-password",
                    json={"current_password": ADMIN_PW, "new_password": "newpass1"}, headers=bearer(a))
    assert r.status_code == 204
    assert refresh(client, b["refresh_token"]).status_code == 401
    assert refresh(client, a["refresh_token"]).status_code == 200
    reasons = {i: r.revoked_reason for i, r in by_id(db).items()}
    assert reasons[b["session_id"]] == "password_changed" and reasons[a["session_id"]] == "rotated"


def _reset_link(db, account_type, account_ref, email):
    raw = f"reset-{account_type.value}-{account_ref}"
    db.add(PasswordResetToken(account_type=account_type, account_ref=account_ref, email=email,
                              token_hash=sha(raw), expires_at=utcnow() + timedelta(minutes=30)))
    db.commit()
    return raw


def test_password_reset_by_link_signs_every_device_out(client, db, teacher):
    t1 = login(client, TEACHER_EMAIL, "pw", remember=True).json()
    login(client, TEACHER_EMAIL, "pw", remember=True, platform="web")     # cookie now in the jar
    s1 = login(client, SUPER_ADMIN_EMAIL, SUPER_PW, remember=True).json()
    raw = _reset_link(db, ResetAccountType.staff, str(teacher.id), TEACHER_EMAIL)
    assert client.post("/api/auth/reset-password", json={"token": raw, "new_password": "fresh123"}).status_code == 200
    assert refresh(client, t1["refresh_token"]).status_code == 401
    assert refresh(client).status_code == 401                              # the web session too
    s1 = refresh(client, s1["refresh_token"]).json()                       # another account: untouched
    # Reset tokens file the singleton accounts under their email; sessions under the JWT sub.
    raw = _reset_link(db, ResetAccountType.super_admin, SUPER_ADMIN_EMAIL, SUPER_ADMIN_EMAIL)
    assert client.post("/api/auth/reset-password", json={"token": raw, "new_password": "fresh123"}).status_code == 200
    assert refresh(client, s1["refresh_token"]).status_code == 401
    assert all(r.revoked_at is not None and r.revoked_reason == "password_reset" for r in rows(db)
               if r.account_type == SessionAccountType.super_admin)
    assert login(client, SUPER_ADMIN_EMAIL, "fresh123").status_code == 200


def test_staff_password_change_signs_the_other_devices_out(client, db, teacher):
    a = login(client, TEACHER_EMAIL, "pw", remember=True, name="Pixel 7").json()
    b = login(client, TEACHER_EMAIL, "pw", remember=True, name="Tablet").json()
    r = client.post("/api/staff/change-password",
                    json={"current_password": "pw", "new_password": "newpass1"}, headers=bearer(a))
    assert r.status_code == 204
    assert refresh(client, b["refresh_token"]).status_code == 401
    assert refresh(client, a["refresh_token"]).status_code == 200
    assert by_id(db)[b["session_id"]].revoked_reason == "password_changed"


def test_admin_password_reset_signs_every_device_out_but_profile_edits_do_not(client, db, teacher):
    a = login(client, TEACHER_EMAIL, "pw", remember=True).json()
    b = login(client, TEACHER_EMAIL, "pw", remember=True, platform="web").json()
    r = client.patch(f"/api/staff/{teacher.id}", json={"reset_password": True}, headers=auth("admin"))
    assert r.status_code == 200 and r.json()["new_password"]
    assert refresh(client, a["refresh_token"]).status_code == 401
    assert refresh(client).status_code == 401
    assert {row.revoked_reason for row in rows(db)} == {"password_reset"}
    # Editing name / classes / menus never does.
    a = login(client, TEACHER_EMAIL, r.json()["new_password"], remember=True).json()
    r = client.patch(f"/api/staff/{teacher.id}",
                     json={"name": "Gurpreet Kaur Gill", "assigned_classes": ["7th"], "allowed_menus": ["dashboard"]},
                     headers=auth("admin"))
    assert r.status_code == 200
    r = refresh(client, a["refresh_token"])
    assert r.status_code == 200 and r.json()["name"] == "Gurpreet Kaur Gill" and r.json()["allowed_classes"] == ["7th"]


def test_deleting_a_teacher_signs_them_out_but_a_pending_request_or_restore_does_not(client, db, teacher):
    a = login(client, TEACHER_EMAIL, "pw", remember=True).json()
    assert client.delete(f"/api/staff/{teacher.id}", headers=auth("admin")).status_code == 200   # -> pending_delete
    a = refresh(client, a["refresh_token"]).json()                                                # still signed in
    assert client.post(f"/api/admin/deletion-requests/staff/{teacher.id}/restore", headers=auth("admin")).status_code == 200
    a = refresh(client, a["refresh_token"]).json()                                                # restore: nothing
    assert client.delete(f"/api/staff/{teacher.id}", headers=auth("super_admin")).status_code == 200  # -> deleted
    assert refresh(client, a["refresh_token"]).status_code == 401
    assert by_id(db)[a["session_id"]].revoked_reason == "account_deleted"


def test_approving_or_purging_a_deletion_signs_the_teacher_out(client, db, teacher):
    a = login(client, TEACHER_EMAIL, "pw", remember=True).json()
    assert client.delete(f"/api/staff/{teacher.id}", headers=auth("admin")).status_code == 200
    assert client.post(f"/api/admin/deletion-requests/staff/{teacher.id}/approve",
                       headers=auth("super_admin")).status_code == 200
    assert refresh(client, a["refresh_token"]).status_code == 401
    other = staff(db, name="Ravi Kumar", email="ravi@kisschool.in", password="pw")
    db.commit()
    b = login(client, "ravi@kisschool.in", "pw", remember=True).json()
    other.status = RecordStatus.deleted
    db.commit()
    assert client.delete(f"/api/admin/deletion-requests/staff/{other.id}", headers=auth("super_admin")).status_code == 204
    reasons = {i: r.revoked_reason for i, r in by_id(db).items()}
    assert reasons[a["session_id"]] == "account_deleted" and reasons[b["session_id"]] == "account_deleted"
    assert refresh(client, b["refresh_token"]).status_code == 401


def test_a_failing_hook_never_breaks_the_request(client, db, teacher, monkeypatch):
    a = login(client, TEACHER_EMAIL, "pw", remember=True).json()

    def boom(*args, **kwargs):
        raise RuntimeError("db hiccup")

    monkeypatch.setattr("app.services.device_sessions.revoke_sessions", boom)
    r = client.post("/api/staff/change-password",
                    json={"current_password": "pw", "new_password": "newpass1"}, headers=bearer(a))
    assert r.status_code == 204
    assert login(client, TEACHER_EMAIL, "newpass1").status_code == 200


# --- logout and session management ----------------------------------------------

def test_logout_works_with_an_expired_bearer_and_clears_the_cookie(client, db, teacher):
    a = login(client, TEACHER_EMAIL, "pw", remember=True).json()
    expired = jwt.encode(
        {"sub": str(teacher.id), "role": "staff", "name": "x", "allowed_classes": [], "allowed_menus": [],
         "iat": utcnow() - timedelta(hours=3), "exp": utcnow() - timedelta(hours=2)},
        settings.JWT_SECRET, algorithm="HS256",
    )
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    r = client.post("/api/auth/logout", json={"refresh_token": a["refresh_token"]},
                    headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 204
    assert refresh(client, a["refresh_token"]).status_code == 401
    assert rows(db)[0].revoked_reason == "logout"
    # Web: no body, the cookie identifies the session; the response expires the cookie.
    login(client, TEACHER_EMAIL, "pw", remember=True, platform="web")
    r = client.post("/api/auth/logout")
    assert r.status_code == 204
    morsel = cookie_of(r)[COOKIE]
    assert morsel["max-age"] == "0" and morsel["path"] == "/api/auth" and morsel.value == ""
    assert refresh(client).status_code == 401
    assert {row.revoked_reason for row in rows(db)} == {"logout"}
    # Nothing to revoke is still a 204 (idempotent, no Bearer at all).
    assert client.post("/api/auth/logout").status_code == 204


def test_sessions_list_marks_the_current_device_and_deletes_own_rows_only(client, db, teacher):
    a = login(client, TEACHER_EMAIL, "pw", remember=True, name="Pixel 7").json()
    b = login(client, TEACHER_EMAIL, "pw", remember=True, platform="web", name="Chrome on Mac").json()
    admin = login(client, ADMIN_EMAIL, ADMIN_PW, remember=True, name="Laptop").json()
    listed = client.get("/api/auth/sessions", headers=bearer(a)).json()
    assert [(s["id"], s["device_name"], s["platform"], s["is_current"]) for s in listed] == [
        (b["session_id"], "Chrome on Mac", "web", False),
        (a["session_id"], "Pixel 7", "android", True),
    ]
    assert all(s["created_at"] and s["last_used_at"] is None for s in listed)
    # After a refresh the device is still one entry (the new id) and shows when it was last used.
    a2 = refresh(client, a["refresh_token"]).json()
    listed = client.get("/api/auth/sessions", headers=bearer(a2)).json()
    mine = next(s for s in listed if s["is_current"])
    assert mine["id"] == a2["session_id"] and mine["last_used_at"] is not None and len(listed) == 2
    # A plain sign-in has no session of its own, so nothing is current.
    plain = login(client, TEACHER_EMAIL, "pw").json()
    assert not any(s["is_current"] for s in client.get("/api/auth/sessions", headers=bearer(plain)).json())
    # Delete: own -> 204 and gone; someone else's or unknown -> 404.
    assert client.delete(f"/api/auth/sessions/{b['session_id']}", headers=bearer(a)).status_code == 204
    assert client.delete(f"/api/auth/sessions/{admin['session_id']}", headers=bearer(a)).status_code == 404
    assert client.delete("/api/auth/sessions/999999", headers=bearer(a)).status_code == 404
    assert {s["id"] for s in client.get("/api/auth/sessions", headers=bearer(a)).json()} == {a2["session_id"]}
    assert client.get("/api/auth/sessions", headers=bearer(admin)).json()[0]["is_current"] is True
    assert by_id(db)[b["session_id"]].revoked_reason == "user"
    assert refresh(client).status_code == 401                       # the deleted web session is dead
    assert client.get("/api/auth/sessions").status_code == 401       # Bearer required


def test_admin_can_sign_a_teacher_out_of_every_device(client, db, teacher):
    a = login(client, TEACHER_EMAIL, "pw", remember=True).json()
    login(client, TEACHER_EMAIL, "pw", remember=True, platform="web")
    a2 = refresh(client, a["refresh_token"]).json()                 # 3 rows, 2 live devices
    assert client.delete(f"/api/staff/{teacher.id}/sessions", headers=auth("staff", ["8th"])).status_code == 403
    assert client.delete("/api/staff/999999/sessions", headers=auth("admin")).status_code == 404
    r = client.delete(f"/api/staff/{teacher.id}/sessions", headers=auth("admin"))
    assert r.status_code == 200 and r.json() == {"revoked": 2}
    assert refresh(client, a2["refresh_token"]).status_code == 401
    assert refresh(client).status_code == 401
    assert all(row.revoked_at is not None and row.revoked_reason == "admin" for row in rows(db))
    assert client.delete(f"/api/staff/{teacher.id}/sessions", headers=auth("super_admin")).json() == {"revoked": 0}


def test_login_prunes_rows_dead_for_thirty_days(client, db, teacher):
    login(client, TEACHER_EMAIL, "pw", remember=True)
    login(client, TEACHER_EMAIL, "pw", remember=True)
    login(client, TEACHER_EMAIL, "pw", remember=True)
    old, recent, expired = rows(db)
    old.revoked_at, old.revoked_reason = utcnow() - timedelta(days=31), "logout"
    recent.revoked_at, recent.revoked_reason = utcnow() - timedelta(days=29), "logout"
    expired.expires_at = utcnow() - timedelta(days=31)
    db.commit()
    assert login(client, TEACHER_EMAIL, "pw").status_code == 200      # prunes even without remember
    assert [r.id for r in rows(db)] == [recent.id]


# --- token parsing ---------------------------------------------------------------

def test_tokens_without_a_session_id_still_parse(client):
    legacy = create_token(sub="1", role="staff", name="x", allowed_classes=["8th"])
    assert "sid" not in decode_token(legacy) and _parse(legacy).sid is None
    assert _parse(create_token(sub="1", role="staff", name="x", allowed_classes=[], sid=7)).sid == 7
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {legacy}"}).status_code == 200


# --- brute force -----------------------------------------------------------------

def test_ten_failures_lock_the_identifier(client, db, teacher):
    for _ in range(10):
        assert login(client, TEACHER_EMAIL, "wrong").status_code == 401
    r = login(client, TEACHER_EMAIL.upper(), "wrong")                 # the key is case-insensitive
    assert r.status_code == 429 and r.json() == {"detail": TOO_MANY_ATTEMPTS_MSG}
    assert login(client, TEACHER_EMAIL, "pw").status_code == 429      # even the right password waits
    assert login(client, ADMIN_EMAIL, ADMIN_PW).status_code == 200    # other identifiers are unaffected
    assert login(client, "nobody@kisschool.in", "x").status_code == 401


def test_a_successful_sign_in_resets_the_failure_count(client, db, teacher):
    for _ in range(9):
        assert login(client, TEACHER_EMAIL, "wrong").status_code == 401
    assert login(client, TEACHER_EMAIL, "pw").status_code == 200
    for _ in range(10):
        assert login(client, TEACHER_EMAIL, "wrong").status_code == 401
    assert login(client, TEACHER_EMAIL, "wrong").status_code == 429


def test_the_lock_lifts_after_fifteen_minutes(client, db, teacher, monkeypatch):
    clock = {"t": 1000.0}
    monkeypatch.setattr("app.routers.auth.time", SimpleNamespace(monotonic=lambda: clock["t"]))
    for _ in range(10):
        login(client, TEACHER_EMAIL, "wrong")
    assert login(client, TEACHER_EMAIL, "pw").status_code == 429
    clock["t"] += 15 * 60 + 1
    assert login(client, TEACHER_EMAIL, "pw").status_code == 200


# --- migration -------------------------------------------------------------------

def test_migration_0021_creates_the_table_the_model_expects(engine):
    migration = _load("0021_device_sessions")
    assert (migration.revision, migration.down_revision) == ("0021_device_sessions", "0020_optional_subjects")
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE device_sessions"))
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
        insp = inspect(conn)
        cols = {c["name"]: c for c in insp.get_columns("device_sessions")}
        assert set(cols) == set(DeviceSession.__table__.columns.keys())
        required = ("account_type", "account_ref", "token_hash", "family_id", "platform", "device_name", "via",
                    "created_at", "expires_at", "absolute_expires_at")
        assert all(cols[c]["nullable"] is False for c in required)
        assert all(cols[c]["nullable"] for c in ("ip", "user_agent", "last_used_at", "rotated_at",
                                                 "replaced_by_id", "revoked_at", "revoked_reason"))
        idx = {i["name"]: i for i in insp.get_indexes("device_sessions")}
        assert idx["ix_device_sessions_token_hash"]["unique"] and idx["ix_device_sessions_token_hash"]["column_names"] == ["token_hash"]
        assert idx["ix_device_sessions_family_id"]["column_names"] == ["family_id"]
        assert idx["ix_device_sessions_account"]["column_names"] == ["account_type", "account_ref"]
        with Operations.context(MigrationContext.configure(conn)):
            migration.downgrade()
        assert "device_sessions" not in inspect(conn).get_table_names()
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()                                   # re-creatable after a downgrade
        assert "device_sessions" in inspect(conn).get_table_names()
