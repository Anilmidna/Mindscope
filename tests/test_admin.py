"""Tests for admin endpoint authentication (C1)."""


def _admin_headers(key: str = "test-admin-key-dev") -> dict:
    return {"X-Admin-Key": key}


class TestAdminAuth:
    def test_get_models_without_key_returns_403(self, client):
        res = client.get("/admin/models")
        assert res.status_code == 403

    def test_get_models_with_wrong_key_returns_403(self, client):
        res = client.get("/admin/models", headers=_admin_headers("wrong-key"))
        assert res.status_code == 403

    def test_get_models_with_correct_key_returns_200(self, client):
        res = client.get("/admin/models", headers=_admin_headers())
        assert res.status_code == 200

    def test_put_models_without_key_returns_403(self, client):
        res = client.put("/admin/models", json={"stage": "report_generation", "model": "sonnet"})
        assert res.status_code == 403

    def test_put_models_with_correct_key_succeeds(self, client):
        res = client.put(
            "/admin/models",
            json={"stage": "report_generation", "model": "sonnet"},
            headers=_admin_headers(),
        )
        assert res.status_code == 200

    def test_post_models_test_without_key_returns_403(self, client):
        res = client.post("/admin/models/test")
        assert res.status_code == 403
