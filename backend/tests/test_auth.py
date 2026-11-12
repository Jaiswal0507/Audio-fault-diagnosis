"""Test Suite for Multi-Tenant Authentication and Database Security."""

import os
from pathlib import Path
import sys
import uuid
from fastapi.testclient import TestClient

# Ensure project root is available for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app
from backend.app.database.database import init_db, get_db
from backend.app.models.models import Organization, User, Machine, Analysis, AnalysisHistory


def test_auth_and_multitenancy():
    client = TestClient(app)
    init_db()

    print("\n" + "=" * 60)
    print("MachineSense - Multi-Tenant Authentication Verification")
    print("=" * 60)

    unique_suffix = uuid.uuid4().hex[:6]
    test_email = f"admin_{unique_suffix}@acme-industrial.com"
    test_password = "SecurePassword123!"
    test_org = f"Acme Industrial {unique_suffix}"

    # -------------------------------------------------------------
    # 1. POST /api/v1/auth/register
    # -------------------------------------------------------------
    print("\n[TEST 1] POST /api/v1/auth/register - Create Organization & Admin User")
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": test_email,
            "password": test_password,
            "organization_name": test_org,
        },
    )
    assert reg_resp.status_code == 201, f"Expected 201, got {reg_resp.status_code}: {reg_resp.text}"
    reg_data = reg_resp.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == test_email
    assert reg_data["user"]["role"] == "admin"
    assert reg_data["organization"]["name"] == test_org
    org_id = reg_data["organization"]["id"]
    print(f"  [PASS] Successfully registered org '{test_org}' (id={org_id}) and user '{test_email}'.")

    # -------------------------------------------------------------
    # 2. Duplicate Registration Rejection
    # -------------------------------------------------------------
    print("\n[TEST 2] POST /api/v1/auth/register - Reject Duplicate Email")
    dup_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": test_email,
            "password": "AnotherPassword",
            "organization_name": "Another Org",
        },
    )
    assert dup_resp.status_code == 400, f"Expected 400, got {dup_resp.status_code}"
    print(f"  [PASS] Correctly rejected duplicate registration: {dup_resp.json()}")

    # -------------------------------------------------------------
    # 3. POST /api/v1/auth/login with OAuth2PasswordRequestForm
    # -------------------------------------------------------------
    print("\n[TEST 3] POST /api/v1/auth/login - Valid Credentials")
    login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": test_email, "password": test_password},
    )
    assert login_resp.status_code == 200, f"Expected 200, got {login_resp.status_code}: {login_resp.text}"
    token_data = login_resp.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    token = token_data["access_token"]
    print(f"  [PASS] Successfully authenticated and obtained JWT: {token[:25]}...")

    # -------------------------------------------------------------
    # 4. POST /api/v1/auth/login with Invalid Credentials
    # -------------------------------------------------------------
    print("\n[TEST 4] POST /api/v1/auth/login - Invalid Password")
    bad_login_resp = client.post(
        "/api/v1/auth/login",
        data={"username": test_email, "password": "WrongPassword!"},
    )
    assert bad_login_resp.status_code == 401, f"Expected 401, got {bad_login_resp.status_code}"
    print(f"  [PASS] Correctly rejected invalid credentials with 401: {bad_login_resp.json()}")

    # -------------------------------------------------------------
    # 5. GET /api/v1/auth/me (Protected Route with JWT)
    # -------------------------------------------------------------
    print("\n[TEST 5] GET /api/v1/auth/me - Authenticated Current User")
    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200, f"Expected 200, got {me_resp.status_code}: {me_resp.text}"
    me_data = me_resp.json()
    assert me_data["email"] == test_email
    assert me_data["organization_id"] == org_id
    assert me_data["organization_name"] == test_org
    print(f"  [PASS] Validated current user identity and tenant affiliation: {me_data}")

    # -------------------------------------------------------------
    # 6. GET /api/v1/auth/me without Token
    # -------------------------------------------------------------
    print("\n[TEST 6] GET /api/v1/auth/me - Unauthenticated Request (Missing Token)")
    no_token_resp = client.get("/api/v1/auth/me")
    assert no_token_resp.status_code == 401, f"Expected 401, got {no_token_resp.status_code}"
    print(f"  [PASS] Correctly blocked unauthorized access with 401: {no_token_resp.json()}")

    # -------------------------------------------------------------
    # 7. Multi-Tenant Model Isolation & Foreign Keys
    # -------------------------------------------------------------
    print("\n[TEST 7] Multi-Tenant DB Relationship Verification (Organization -> Machine/Analysis)")
    db_gen = get_db()
    db = next(db_gen)
    try:
        # Create a tenant machine and analysis
        machine_code = f"MCH-TEST-{unique_suffix}"
        tenant_machine = Machine(
            machine_code=machine_code,
            machine_type="motor",
            name="Testing Tenant Motor",
            organization_id=org_id,
        )
        db.add(tenant_machine)
        db.flush()

        tenant_analysis = Analysis(
            analysis_id=f"AN-TEST-{unique_suffix}",
            machine_code=machine_code,
            machine_type="motor",
            condition="normal",
            score=0.98,
            organization_id=org_id,
        )
        db.add(tenant_analysis)
        db.commit()

        # Query back via Organization relationships
        org_record = db.query(Organization).filter(Organization.id == org_id).first()
        assert org_record is not None
        assert len(org_record.users) >= 1
        assert any(u.email == test_email for u in org_record.users)
        assert any(m.machine_code == machine_code for m in org_record.machines)
        assert any(a.analysis_id == f"AN-TEST-{unique_suffix}" for a in org_record.analyses)

        # Verify AnalysisHistory alias works identically
        history_record = db.query(AnalysisHistory).filter(AnalysisHistory.analysis_id == f"AN-TEST-{unique_suffix}").first()
        assert history_record is not None
        assert history_record.organization_id == org_id
        print("  [PASS] Verified Organization-scoped relationships and foreign keys for Machine and Analysis.")
    finally:
        db.close()

    print("\n" + "=" * 60)
    print("All Authentication & Multi-Tenancy Tests PASSED Successfully!")
    print("=" * 60)


if __name__ == "__main__":
    test_auth_and_multitenancy()
