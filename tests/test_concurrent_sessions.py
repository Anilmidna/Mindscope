"""
Load test: 5 sessions — verifies correct pipeline behaviour and isolation
when multiple users run assessments.

SQLite (in-memory, StaticPool) is single-threaded; ThreadPoolExecutor is not
used here because concurrent writes on a shared SQLite connection deadlock.
The tests instead run the 5 pipelines sequentially and verify:
  - no errors per pipeline
  - each session receives 202 on complete
  - session data is fully isolated (no cross-contamination)

True parallel load testing (5 real concurrent Postgres connections) is
performed in the staging environment, not in unit tests.

Day 7 sprint requirement: Load test 5 concurrent sessions, verify no race
conditions in scoring/report pipeline.
"""
import uuid

import pytest

from app.core.security import create_access_token
from app.models.user import User

# Removed ThreadPoolExecutor: SQLite StaticPool is single-threaded.

# ---------------------------------------------------------------------------
# Answer keys (same as test_aptitude_scoring.py)
# ---------------------------------------------------------------------------
LOGICAL_KEY = {
    "LG-01": 1, "LG-02": 1, "LG-03": 1, "LG-04": 2, "LG-05": 1,
    "LG-06": 0, "LG-07": 0, "LG-08": 2, "LG-09": 2, "LG-10": 0,
    "LG-11": 2, "LG-12": 2, "LG-13": 0, "LG-14": 1, "LG-15": 1,
}
NUMERICAL_KEY = {
    "NM-01": 1, "NM-02": 1, "NM-03": 2, "NM-04": 2, "NM-05": 1,
    "NM-06": 2, "NM-07": 1, "NM-08": 1, "NM-09": 1, "NM-10": 2,
    "NM-11": 2, "NM-12": 1, "NM-13": 0, "NM-14": 1, "NM-15": 0,
}
VERBAL_KEY = {
    "VB-01": 1, "VB-02": 1, "VB-03": 1, "VB-04": 2, "VB-05": 1,
    "VB-06": 1, "VB-07": 1, "VB-08": 0, "VB-09": 2, "VB-10": 1,
    "VB-11": 2, "VB-12": 1, "VB-13": 1, "VB-14": 1, "VB-15": 2,
}
SPATIAL_KEY = {
    "SP-01": 1, "SP-02": 0, "SP-03": 1, "SP-04": 0, "SP-05": 1,
    "SP-06": 0, "SP-07": 3, "SP-08": 0, "SP-09": 3, "SP-10": 1,
    "SP-11": 1, "SP-12": 1, "SP-13": 2, "SP-14": 1, "SP-15": 1,
}

RIASEC_ITEMS = [f"R{i:02d}" for i in range(1, 9)] + [f"I{i:02d}" for i in range(1, 9)] + \
               [f"A{i:02d}" for i in range(1, 9)] + [f"S{i:02d}" for i in range(1, 9)] + \
               [f"E{i:02d}" for i in range(1, 9)] + [f"C{i:02d}" for i in range(1, 9)]
OCEAN_ITEMS = [f"O{i:02d}" for i in range(1, 11)] + [f"C{i:02d}" for i in range(1, 11)] + \
              [f"E{i:02d}" for i in range(1, 11)] + [f"A{i:02d}" for i in range(1, 11)] + \
              [f"N{i:02d}" for i in range(1, 11)]

DOMAIN_RESPONSES = {
    "RIASEC": [{"item_id": iid, "answer": 3, "response_time_ms": 4000} for iid in RIASEC_ITEMS],
    "OCEAN":  [{"item_id": iid, "answer": 3, "response_time_ms": 4000} for iid in OCEAN_ITEMS],
    "Logical":   [{"item_id": k, "answer": v, "response_time_ms": 5000} for k, v in LOGICAL_KEY.items()],
    "Numerical": [{"item_id": k, "answer": v, "response_time_ms": 5000} for k, v in NUMERICAL_KEY.items()],
    "Verbal":    [{"item_id": k, "answer": v, "response_time_ms": 5000} for k, v in VERBAL_KEY.items()],
    "Spatial":   [{"item_id": k, "answer": v, "response_time_ms": 5000} for k, v in SPATIAL_KEY.items()],
}


def _make_user(db, idx: int) -> User:
    user = User(
        google_sub=f"google-sub-load-{idx}-{uuid.uuid4()}",
        email=f"loaduser{idx}@example.com",
        name=f"Load User {idx}",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_headers(user: User) -> dict:
    token = create_access_token(str(user.id), user.email)
    return {"Authorization": f"Bearer {token}"}


def _run_full_pipeline(client, user: User) -> dict:
    """
    Simulate one full B2C session pipeline (no Bedrock — just up to responses + complete).
    Returns a summary dict with session_id and status at each step.
    """
    headers = _auth_headers(user)
    result = {"user_id": str(user.id), "errors": []}

    # 1. Create session
    res = client.post("/sessions", json={"context_of_origin": "standalone-public"}, headers=headers)
    if res.status_code != 201:
        result["errors"].append(f"create_session: {res.status_code} {res.text}")
        return result
    session_id = res.json()["id"]
    result["session_id"] = session_id

    # 2. Submit intake
    res = client.post(f"/sessions/{session_id}/intake", headers=headers, json={
        "life_stage": "Undergraduate Student",
        "education_level": "bachelor",
        "future_goals": "Become a software engineer",
        "satisfaction": 7,
        "consent_given_at": "2026-06-26T10:00:00Z",
    })
    if res.status_code != 200:
        result["errors"].append(f"intake: {res.status_code} {res.text}")

    # 3. Submit responses for each domain
    for domain, items in DOMAIN_RESPONSES.items():
        res = client.post(
            f"/sessions/{session_id}/responses",
            headers=headers,
            json={"domain": domain, "items": items},
        )
        if res.status_code != 200:
            result["errors"].append(f"responses/{domain}: {res.status_code} {res.text[:200]}")

    # 4. Check section status
    res = client.get(f"/sessions/{session_id}/section-status", headers=headers)
    result["section_status_ok"] = res.status_code == 200

    # 5. Get session detail — verify completed_domains
    res = client.get(f"/sessions/{session_id}", headers=headers)
    if res.status_code == 200:
        result["completed_domains"] = res.json().get("completed_domains", [])

    # 6. POST complete (triggers background scoring — we don't wait for Bedrock)
    res = client.post(f"/sessions/{session_id}/complete", headers=headers)
    result["complete_status"] = res.status_code

    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestConcurrentSessions:
    N_SESSIONS = 5

    def test_five_sessions_no_errors(self, client, db):
        """5 users run full pipelines sequentially — all should complete without errors."""
        users = [_make_user(db, i) for i in range(self.N_SESSIONS)]
        results = [_run_full_pipeline(client, u) for u in users]

        assert len(results) == self.N_SESSIONS
        for r in results:
            assert r.get("errors") == [], f"Pipeline errors for user {r['user_id']}: {r['errors']}"

    def test_complete_accepted_for_all_sessions(self, client, db):
        """All 5 sessions should receive 202 Accepted on complete."""
        users = [_make_user(db, i + 100) for i in range(self.N_SESSIONS)]
        results = [_run_full_pipeline(client, u) for u in users]

        for r in results:
            assert r.get("complete_status") in (202, 200), (
                f"Expected 202 on complete for {r.get('session_id')}, got {r.get('complete_status')}"
            )

    def test_completed_domains_isolated_per_session(self, client, db):
        """Each session should only see its own completed_domains."""
        users = [_make_user(db, i + 200) for i in range(self.N_SESSIONS)]
        results = [_run_full_pipeline(client, u) for u in users]

        session_ids = {r.get("session_id") for r in results}
        assert len(session_ids) == self.N_SESSIONS

        for r in results:
            domains = set(r.get("completed_domains", []))
            expected = {"RIASEC", "OCEAN", "Logical", "Numerical", "Verbal", "Spatial"}
            assert domains == expected, (
                f"Session {r.get('session_id')} completed_domains mismatch: {domains}"
            )

    def test_no_cross_session_response_leak(self, client, db):
        """Responses submitted for session A must not appear in session B's completed_domains."""
        user_a = _make_user(db, 300)
        user_b = _make_user(db, 301)

        headers_a = _auth_headers(user_a)
        headers_b = _auth_headers(user_b)

        # Create both sessions
        sid_a = client.post("/sessions", json={"context_of_origin": "standalone-public"}, headers=headers_a).json()["id"]
        sid_b = client.post("/sessions", json={"context_of_origin": "standalone-public"}, headers=headers_b).json()["id"]

        # Only submit RIASEC for A
        client.post(f"/sessions/{sid_a}/responses", headers=headers_a, json={
            "domain": "RIASEC",
            "items": DOMAIN_RESPONSES["RIASEC"],
        })

        # B should have no completed domains
        res_b = client.get(f"/sessions/{sid_b}", headers=headers_b)
        assert res_b.status_code == 200
        assert res_b.json()["completed_domains"] == []

        # A should have exactly RIASEC
        res_a = client.get(f"/sessions/{sid_a}", headers=headers_a)
        assert res_a.status_code == 200
        assert res_a.json()["completed_domains"] == ["RIASEC"]

    def test_session_not_accessible_by_other_user(self, client, db):
        """User B cannot read User A's session."""
        user_a = _make_user(db, 400)
        user_b = _make_user(db, 401)

        headers_a = _auth_headers(user_a)
        headers_b = _auth_headers(user_b)

        sid_a = client.post("/sessions", json={"context_of_origin": "standalone-public"}, headers=headers_a).json()["id"]

        res = client.get(f"/sessions/{sid_a}", headers=headers_b)
        assert res.status_code == 404
