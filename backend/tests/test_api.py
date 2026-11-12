"""Integration and API tests for MachineSense Backend.

Tests health check, JWT authentication enforcement, multi-tenant isolation,
and audio analysis endpoints using FastAPI TestClient.
"""

import io
import json
from pathlib import Path
import sys
import uuid
import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

# Ensure project root is available for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.main import app
from backend.app.database.database import get_db, init_db
from backend.app.models.models import Organization, User, Machine, Analysis
from backend.app.core.security import create_access_token, get_password_hash


def setup_test_auth_headers(db, org_name="Test Engineering Lab", email="tester@machinesense.local"):
    """Create or retrieve a test organization, test user, and valid JWT bearer auth headers."""
    test_org = db.query(Organization).filter(Organization.name == org_name).first()
    if not test_org:
        test_org = Organization(name=org_name)
        db.add(test_org)
        db.flush()

    test_user = db.query(User).filter(User.email == email).first()
    if not test_user:
        test_user = User(
            email=email,
            hashed_password=get_password_hash("TestSecure123!"),
            role="admin",
            organization_id=test_org.id,
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
    else:
        test_user.organization_id = test_org.id
        db.commit()

    token = create_access_token(
        data={
            "sub": test_user.email,
            "org_id": test_org.id,
            "role": test_user.role,
        }
    )
    return {"Authorization": f"Bearer {token}"}, test_org.id, test_user.id


def run_api_tests():
    """Run test suite for health check, auth security, multi-tenancy, and analyze endpoints."""
    print("=" * 60)
    print("MachineSense - FastAPI Endpoints & Multi-Tenant JWT Verification")
    print("=" * 60)

    client = TestClient(app)
    init_db()

    db_gen = get_db()
    db = next(db_gen)
    try:
        auth_headers, org_id, user_id = setup_test_auth_headers(db)
    finally:
        db.close()

    # -------------------------------------------------------------
    # Test 1: GET /api/v1/health (Public Endpoint)
    # -------------------------------------------------------------
    print("\n[TEST 1] GET /api/v1/health - Public Health Check")
    health_resp = client.get("/api/v1/health")
    assert health_resp.status_code == 200, f"Expected 200, got {health_resp.status_code}"
    assert health_resp.json() == {"status": "MachineSense API is running"}
    print(f"  [PASS] Status code: {health_resp.status_code}, Response: {health_resp.json()}")

    # -------------------------------------------------------------
    # Test 2: Security Check - POST /api/v1/analyze without Auth Token
    # -------------------------------------------------------------
    print("\n[TEST 2] POST /api/v1/analyze - Unauthenticated Request (Missing Token)")
    unauth_resp = client.post(
        "/api/v1/analyze",
        data={"machine_id": "MCH-001"},
        files={"file": ("notes.wav", b"dummy", "audio/wav")},
    )
    assert unauth_resp.status_code == 401, f"Expected 401 Unauthorized, got {unauth_resp.status_code}"
    print(f"  [PASS] Correctly rejected unauthenticated analysis request with 401: {unauth_resp.json()}")

    # -------------------------------------------------------------
    # Test 3: POST /api/v1/analyze with invalid extension (.txt)
    # -------------------------------------------------------------
    print("\n[TEST 3] POST /api/v1/analyze with unsupported extension (.txt) [Authenticated]")
    bad_ext_resp = client.post(
        "/api/v1/analyze",
        headers=auth_headers,
        data={"machine_id": "MCH-001"},
        files={"file": ("notes.txt", b"plain text data", "text/plain")},
    )
    assert bad_ext_resp.status_code == 400, f"Expected 400, got {bad_ext_resp.status_code}"
    print(f"  [PASS] Correctly rejected unsupported extension: {bad_ext_resp.json()}")

    # -------------------------------------------------------------
    # Test 4: POST /api/v1/analyze with dummy corrupted audio (renamed .wav)
    # -------------------------------------------------------------
    print("\n[TEST 4] POST /api/v1/analyze with corrupted audio content [Authenticated]")
    corrupt_audio_bytes = b"This is invalid text data disguised as a .wav file."
    corrupt_resp = client.post(
        "/api/v1/analyze",
        headers=auth_headers,
        data={"machine_id": "MCH-001", "machine_type": "bearing"},
        files={"file": ("corrupt_audio.wav", corrupt_audio_bytes, "audio/wav")},
    )
    assert corrupt_resp.status_code in [422, 500], f"Expected 422 or 500, got {corrupt_resp.status_code}"
    print(f"  [PASS] Gracefully caught audio decode failure with status {corrupt_resp.status_code}: {corrupt_resp.json()}")

    # -------------------------------------------------------------
    # Test 5: POST /api/v1/analyze with valid synthetic WAV audio (Bearing - CWRU MultiClass)
    # -------------------------------------------------------------
    print("\n[TEST 5] POST /api/v1/analyze with valid synthetic WAV audio (Bearing - CWRU MultiClass)")
    sr = 16000
    duration = 0.5
    t = np.linspace(0, duration, int(sr * duration), endpoint=False, dtype=np.float32)
    tone = 0.6 * np.sin(2 * np.pi * 400.0 * t)

    wav_buffer = io.BytesIO()
    sf.write(wav_buffer, tone, sr, format="WAV")
    wav_bytes = wav_buffer.getvalue()

    bearing_machine_id = f"MCH-BEARING-{uuid.uuid4().hex[:6]}"
    success_resp = client.post(
        "/api/v1/analyze",
        headers=auth_headers,
        data={"machine_id": bearing_machine_id, "machine_type": "bearing"},
        files={"file": ("sample_bearing.wav", wav_bytes, "audio/wav")},
    )

    assert success_resp.status_code == 200, f"Expected 200, got {success_resp.status_code}: {success_resp.text}"
    body = success_resp.json()

    # Validate structure matching diagnosis response schema
    assert "analysis_id" in body and body["analysis_id"].startswith("AN-")
    assert body["machine_id"] == bearing_machine_id
    assert body["machine_type"] == "bearing"
    assert body["status"] in ["normal", "anomaly", "fault"]
    assert isinstance(body["score"], (int, float))
    assert body["model"]["name"] == "CWRU_MultiClass_CNN"
    assert "features" in body
    assert "waveform_data" in body and len(body["waveform_data"]) > 0
    assert "fft_data" in body and len(body["fft_data"]) > 0
    assert body["organization_id"] == org_id
    assert body.get("persisted") is True, f"Expected persisted=True, got {body.get('persisted')}"
    print("  [PASS] Verified Bearing diagnosis matches CWRU MultiClass CNN with organization isolation and persisted=True!")

    # -------------------------------------------------------------
    # Test 6: POST /api/v1/analyze with Fan Model (Advanced_CNN_Cascade)
    # -------------------------------------------------------------
    print("\n[TEST 6] POST /api/v1/analyze with Fan Model (Advanced_CNN_Cascade)")
    fan_machine_id = f"MCH-FAN-{uuid.uuid4().hex[:6]}"
    fan_resp = client.post(
        "/api/v1/analyze",
        headers=auth_headers,
        data={"machine_id": fan_machine_id, "machine_type": "fan"},
        files={"file": ("sample_fan.wav", wav_bytes, "audio/wav")},
    )
    assert fan_resp.status_code == 200, f"Expected 200, got {fan_resp.status_code}: {fan_resp.text}"
    fan_body = fan_resp.json()
    assert fan_body["model"]["name"] == "Advanced_CNN_Cascade"
    assert fan_body["organization_id"] == org_id
    print(f"  [PASS] Correctly routed fan to Advanced_CNN_Cascade: {fan_body['model']['name']}")

    # -------------------------------------------------------------
    # Test 7: POST /api/v1/analyze with Unavailable Model ('pump')
    # -------------------------------------------------------------
    print("\n[TEST 7] POST /api/v1/analyze with unavailable machine_type ('pump')")
    unavail_resp = client.post(
        "/api/v1/analyze",
        headers=auth_headers,
        data={"machine_id": "MCH-PUMP-001", "machine_type": "pump"},
        files={"file": ("sample_pump.wav", wav_bytes, "audio/wav")},
    )
    assert unavail_resp.status_code == 400, f"Expected 400, got {unavail_resp.status_code}"
    expected_detail = "Diagnostic model for 'pump' is currently unavailable or in development."
    assert unavail_resp.json()["detail"] == expected_detail
    print(f"  [PASS] Correctly rejected unavailable model with 400: {unavail_resp.json()}")

    # -------------------------------------------------------------
    # Test 8: POST /api/v1/analyze with Variable-Length Audio (2.5 seconds)
    # -------------------------------------------------------------
    print("\n[TEST 8] POST /api/v1/analyze with variable-length audio (2.5 seconds)")
    duration_long = 2.5
    t_long = np.linspace(0, duration_long, int(sr * duration_long), endpoint=False, dtype=np.float32)
    tone_long = 0.5 * np.sin(2 * np.pi * 350.0 * t_long)
    buf_long = io.BytesIO()
    sf.write(buf_long, tone_long, sr, format="WAV")

    long_resp = client.post(
        "/api/v1/analyze",
        headers=auth_headers,
        data={"machine_id": "MCH-VAR-001", "machine_type": "motor"},
        files={"file": ("sample_var_length.wav", buf_long.getvalue(), "audio/wav")},
    )
    assert long_resp.status_code == 200, f"Expected 200, got {long_resp.status_code}: {long_resp.text}"
    long_body = long_resp.json()
    assert long_body["status"] in ["normal", "anomaly", "fault"]
    assert long_body["model"]["name"] == "CWRU_MultiClass_CNN"
    print(f"  [PASS] Variable-length audio processed smoothly with score: {long_body['score']}")

    # -------------------------------------------------------------
    # Test 9: Security on History & Machine Endpoints
    # -------------------------------------------------------------
    print("\n[TEST 9] Security Check - GET /history and /machines without Auth Token")
    hist_unauth = client.get("/api/v1/history")
    assert hist_unauth.status_code == 401, f"Expected 401 on /history, got {hist_unauth.status_code}"

    mach_unauth = client.get("/api/v1/machines")
    assert mach_unauth.status_code == 401, f"Expected 401 on /machines, got {mach_unauth.status_code}"

    mach_hist_unauth = client.get(f"/api/v1/machines/{bearing_machine_id}/history")
    assert mach_hist_unauth.status_code == 401, f"Expected 401 on /machines/{{id}}/history, got {mach_hist_unauth.status_code}"
    print("  [PASS] Correctly blocked unauthorized access to history and machine endpoints with 401!")

    # -------------------------------------------------------------
    # Test 10: Multi-Tenant Data Isolation (Cross-Organization Verification)
    # -------------------------------------------------------------
    print("\n[TEST 10] Multi-Tenant Data Isolation (Cross-Organization Boundary Verification)")
    db_gen = get_db()
    db = next(db_gen)
    try:
        # Create second independent tenant organization & user
        tenant_b_headers, org_b_id, user_b_id = setup_test_auth_headers(
            db,
            org_name="Tenant B Competitor Robotics",
            email=f"admin_{uuid.uuid4().hex[:6]}@tenant-b.com",
        )
    finally:
        db.close()

    # User A queries their own machine history
    user_a_hist = client.get(f"/api/v1/machines/{bearing_machine_id}/history", headers=auth_headers)
    assert user_a_hist.status_code == 200
    user_a_data = user_a_hist.json()
    assert user_a_data["total"] >= 1
    assert any(a["machine_id"] == bearing_machine_id for a in user_a_data["analyses"])
    print(f"  [PASS] Tenant A successfully retrieved {user_a_data['total']} analyses for machine '{bearing_machine_id}'.")

    # User B queries Tenant A's machine history -> must return 0 records!
    user_b_hist = client.get(f"/api/v1/machines/{bearing_machine_id}/history", headers=tenant_b_headers)
    assert user_b_hist.status_code == 200
    user_b_data = user_b_hist.json()
    assert user_b_data["total"] == 0, f"Isolation failure! Tenant B saw {user_b_data['total']} records of Tenant A!"
    assert len(user_b_data["analyses"]) == 0
    print("  [PASS] Tenant B queried Tenant A's machine and received 0 records (isolated)!")

    # User B queries list of machines -> Tenant A's machine must NOT appear in Tenant B's machine list!
    user_b_machines = client.get("/api/v1/machines", headers=tenant_b_headers)
    assert user_b_machines.status_code == 200
    user_b_mach_data = user_b_machines.json()
    assert not any(m["machine_code"] == bearing_machine_id for m in user_b_mach_data["machines"])
    print("  [PASS] Tenant B's machine list does not leak Tenant A's registered machines!")

    # Verify Database row has organization_id populated (NOT NULL)
    db_gen = get_db()
    db = next(db_gen)
    try:
        persisted_analysis = db.query(Analysis).filter(Analysis.machine_code == bearing_machine_id).first()
        assert persisted_analysis is not None
        assert persisted_analysis.organization_id is not None
        assert persisted_analysis.organization_id == org_id
        print(f"  [PASS] Database row Analysis(id={persisted_analysis.analysis_id}) organization_id={persisted_analysis.organization_id} is strictly verified NOT NULL.")
    finally:
        db.close()

    # -------------------------------------------------------------
    # Test 11: N1 Cross-Tenant Machine Code Collision Check
    # -------------------------------------------------------------
    print("\n[TEST 11] Cross-Tenant Same Machine Code Reuse (No Collision)")
    # Tenant B analyzes audio on the identical machine_id as Tenant A
    tenant_b_same_machine_resp = client.post(
        "/api/v1/analyze",
        headers=tenant_b_headers,
        data={"machine_id": bearing_machine_id, "machine_type": "bearing"},
        files={"file": ("sample_bearing.wav", wav_bytes, "audio/wav")},
    )
    assert tenant_b_same_machine_resp.status_code == 200, f"Tenant B failed to reuse machine_id: {tenant_b_same_machine_resp.text}"
    print(f"  [PASS] Tenant B successfully analyzed audio using the same machine ID '{bearing_machine_id}' without collision!")

    # Verify Tenant A and Tenant B still have separated histories for this machine code
    user_a_hist_after = client.get(f"/api/v1/machines/{bearing_machine_id}/history", headers=auth_headers).json()
    user_b_hist_after = client.get(f"/api/v1/machines/{bearing_machine_id}/history", headers=tenant_b_headers).json()
    assert user_a_hist_after["total"] >= 1
    assert user_b_hist_after["total"] >= 1
    assert all(a["organization_id"] == org_id for a in user_a_hist_after["analyses"])
    assert all(a["organization_id"] == org_b_id for a in user_b_hist_after["analyses"])
    print("  [PASS] Both tenants maintain isolated, collision-free histories for the same machine ID.")

    print("\n" + "=" * 60)
    # -------------------------------------------------------------
    # Test 12: File Size Limit (10 MB Payload Too Large -> 413)
    # -------------------------------------------------------------
    print("\n[TEST 12] POST /api/v1/analyze with payload > 10 MB (Payload Too Large)")
    large_payload = b"X" * (10 * 1024 * 1024 + 512)  # Exceeds 10 MB limit
    large_resp = client.post(
        "/api/v1/analyze",
        headers=auth_headers,
        data={"machine_id": "MCH-001", "machine_type": "bearing"},
        files={"file": ("oversized.wav", large_payload, "audio/wav")},
    )
    assert large_resp.status_code == 413, f"Expected 413 Payload Too Large, got {large_resp.status_code}: {large_resp.text}"
    print(f"  [PASS] Correctly rejected oversized file (>10MB) with 413: {large_resp.json()}")

    # -------------------------------------------------------------
    # Test 13: Duration Limit (>30.0s -> 400 Bad Request)
    # -------------------------------------------------------------
    print("\n[TEST 13] POST /api/v1/analyze with audio duration > 30 seconds")
    sr_long = 8000
    duration_long = 32.0  # 32 seconds exceeds 30.0s limit
    long_samples = np.zeros(int(sr_long * duration_long), dtype=np.float32)
    long_buf = io.BytesIO()
    sf.write(long_buf, long_samples, sr_long, format="WAV")
    long_bytes = long_buf.getvalue()

    long_resp = client.post(
        "/api/v1/analyze",
        headers=auth_headers,
        data={"machine_id": "MCH-001", "machine_type": "bearing"},
        files={"file": ("too_long.wav", long_bytes, "audio/wav")},
    )
    assert long_resp.status_code in [400, 422], f"Expected 400 or 422, got {long_resp.status_code}: {long_resp.text}"
    print(f"  [PASS] Correctly rejected audio exceeding 30s limit with {long_resp.status_code}: {long_resp.json()}\n")

    # -------------------------------------------------------------
    # Test 14: Machine Type Conflict Check (409 Conflict)
    # -------------------------------------------------------------
    print("[TEST 14] POST /api/v1/analyze with conflicting machine_type on existing machine (409 Conflict)")
    conflict_resp = client.post(
        "/api/v1/analyze",
        headers=auth_headers,
        data={"machine_id": bearing_machine_id, "machine_type": "fan"},  # Already registered as 'bearing'
        files={"file": ("sample.wav", wav_bytes, "audio/wav")},
    )
    assert conflict_resp.status_code == 409, f"Expected 409 Conflict, got {conflict_resp.status_code}: {conflict_resp.text}"
    assert "Machine type conflict" in conflict_resp.json().get("detail", "")
    print(f"  [PASS] Correctly rejected conflicting machine_type with 409: {conflict_resp.json()}\n")

    print("All FastAPI Backend & Multi-Tenant Security Tests PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_api_tests()
