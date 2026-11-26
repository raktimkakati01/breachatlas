"""Admin area: authentication, role authorization, review workflow, MFA, and audit log."""

from __future__ import annotations

import pyotp

# --- Authentication ---


def test_login_logout_me(admin_ctx):
    email = admin_ctx.make_user("admin")
    c = admin_ctx.client_for(email)

    me = c.get("/admin/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == email
    assert me.json()["role"] == "admin"

    assert c.post("/admin/auth/logout").status_code == 200
    # cookie revoked → no longer authenticated
    assert c.get("/admin/auth/me").status_code == 401


def test_bad_password_is_401_and_generic(admin_ctx):
    email = admin_ctx.make_user("admin")
    resp = admin_ctx.anon.post(
        "/admin/auth/login", json={"email": email, "password": "wrong-password-xx"}
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid credentials"


def test_inactive_user_cannot_log_in(admin_ctx):
    email = admin_ctx.make_user("editor", email="off@example.com", active=False)
    resp = admin_ctx.anon.post(
        "/admin/auth/login", json={"email": email, "password": admin_ctx.password}
    )
    assert resp.status_code == 401


def test_unauthenticated_requests_are_rejected(admin_ctx):
    assert admin_ctx.anon.get("/admin/auth/me").status_code == 401
    assert admin_ctx.anon.get("/admin/breaches").status_code == 401
    assert admin_ctx.anon.get("/admin/audit").status_code == 401


# --- Role authorization matrix ---


def test_editor_cannot_manage_users_or_review(admin_ctx):
    admin_ctx.make_user("editor")
    c = admin_ctx.client_for("editor@example.com")

    # user management is admin-only
    assert c.get("/admin/users").status_code == 403
    assert (
        c.post(
            "/admin/users",
            json={"email": "x@example.com", "password": "a-very-long-pass", "role": "editor"},
        ).status_code
        == 403
    )
    # audit log is admin-only
    assert c.get("/admin/audit").status_code == 403

    # editor may create a draft but may NOT approve/publish it
    c.post(
        "/admin/breaches",
        json={
            "organization": "Draft Co",
            "country": "US",
            "sector": "Tech",
            "date_disclosed": "2025-01-01",
        },
    )
    slug = c.get("/admin/breaches").json()[0]["slug"]
    c.post(f"/admin/breaches/{slug}/submit")
    assert c.post(f"/admin/breaches/{slug}/approve").status_code == 403


def test_reviewer_can_review_but_not_manage_users(admin_ctx):
    admin_ctx.make_user("reviewer")
    c = admin_ctx.client_for("reviewer@example.com")
    assert c.get("/admin/breaches").status_code == 200  # can read queue
    assert c.get("/admin/users").status_code == 403  # cannot manage users


def test_admin_can_create_users(admin_ctx):
    admin_ctx.make_user("admin")
    c = admin_ctx.client_for("admin@example.com")
    resp = c.post(
        "/admin/users",
        json={"email": "new@example.com", "password": "a-very-long-pass", "role": "reviewer"},
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "reviewer"
    # duplicate email rejected
    assert (
        c.post(
            "/admin/users",
            json={"email": "new@example.com", "password": "a-very-long-pass", "role": "editor"},
        ).status_code
        == 409
    )


# --- Review workflow / state machine ---


def test_full_review_workflow_to_publish(admin_ctx):
    admin_ctx.make_user("editor")
    admin_ctx.make_user("reviewer")
    editor = admin_ctx.client_for("editor@example.com")
    reviewer = admin_ctx.client_for("reviewer@example.com")

    created = editor.post(
        "/admin/breaches",
        json={
            "organization": "Workflow Corp",
            "country": "US",
            "sector": "Finance",
            "date_disclosed": "2025-02-02",
            "summary": "candidate",
        },
    ).json()
    slug = created["slug"]
    assert created["review_status"] == "draft"
    assert created["is_published"] is False

    assert editor.post(f"/admin/breaches/{slug}/submit").json()["review_status"] == "in_review"
    assert reviewer.post(f"/admin/breaches/{slug}/approve").json()["review_status"] == "approved"

    published = reviewer.post(f"/admin/breaches/{slug}/publish").json()
    assert published["review_status"] == "published"
    assert published["is_published"] is True


def test_invalid_transition_is_409(admin_ctx):
    admin_ctx.make_user("reviewer")
    c = admin_ctx.client_for("reviewer@example.com")
    c.post(
        "/admin/breaches",
        json={
            "organization": "Jump Co",
            "country": "US",
            "sector": "Tech",
            "date_disclosed": "2025-03-03",
        },
    )
    slug = c.get("/admin/breaches").json()[0]["slug"]
    # cannot publish a draft (must go through in_review → approved)
    assert c.post(f"/admin/breaches/{slug}/publish").status_code == 409


# --- MFA (TOTP) ---


def test_mfa_enroll_and_enforced_login(admin_ctx):
    admin_ctx.make_user("admin")
    c = admin_ctx.client_for("admin@example.com")

    secret = c.post("/admin/auth/mfa/enroll").json()["secret"]
    code = pyotp.TOTP(secret).now()
    assert c.post("/admin/auth/mfa/verify", json={"code": code}).json()["mfa_enabled"] is True

    c.post("/admin/auth/logout")

    # login without a code now fails...
    assert (
        admin_ctx.anon.post(
            "/admin/auth/login",
            json={"email": "admin@example.com", "password": admin_ctx.password},
        ).status_code
        == 401
    )
    # ...and with a valid code succeeds
    ok = admin_ctx.anon.post(
        "/admin/auth/login",
        json={
            "email": "admin@example.com",
            "password": admin_ctx.password,
            "totp_code": pyotp.TOTP(secret).now(),
        },
    )
    assert ok.status_code == 200


# --- Audit log ---


def test_actions_are_audited(admin_ctx):
    admin_ctx.make_user("admin")
    admin_ctx.make_user("reviewer")
    admin = admin_ctx.client_for("admin@example.com")
    reviewer = admin_ctx.client_for("reviewer@example.com")

    reviewer.post(
        "/admin/breaches",
        json={
            "organization": "Audit Co",
            "country": "US",
            "sector": "Tech",
            "date_disclosed": "2025-04-04",
        },
    )
    slug = reviewer.get("/admin/breaches").json()[0]["slug"]
    reviewer.post(f"/admin/breaches/{slug}/submit")

    actions = {row["action"] for row in admin.get("/admin/audit").json()}
    assert "login.success" in actions
    assert "breach.create" in actions
    assert "breach.submit" in actions
