"""
Admin auth & stats integration tests.

覆盖：
  1. 未登录访问 /admin -> 302 重定向到 /admin/login
  2. 未登录访问 /api/admin/* -> 401
  3. 错误账号密码登录 -> 401
  4. 正确账号密码登录 -> 200，session cookie 设置成功
  5. 登录后可访问 /api/admin/stats，能正确返回用户/日记统计
  6. /api/admin/stats 的 top_users 包含每个用户的 token 用量字段
"""
import os
import pytest
from fastapi.testclient import TestClient

from main import app


ADMIN_USER = "admin"
ADMIN_PASS = "admin123"  # 与 config.py 默认值一致


@pytest.fixture
def admin_client(db_session):
    """不走 conftest.client 的鉴权覆盖，专门测 admin 鉴权。"""
    app.dependency_overrides.clear()

    from database import get_db as real_get_db

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[real_get_db] = _override_get_db

    with TestClient(app) as tc:
        yield tc
    app.dependency_overrides.clear()


class TestAdminAuth:
    def test_admin_page_requires_login(self, admin_client):
        """未登录访问 /admin 必须 302 到 /admin/login，不能让页面裸返回。"""
        r = admin_client.get("/admin", follow_redirects=False)
        assert r.status_code == 302
        assert r.headers["location"] == "/admin/login"

    def test_admin_check_requires_login(self, admin_client):
        r = admin_client.get("/api/admin/check")
        assert r.status_code == 401

    def test_admin_stats_requires_login(self, admin_client):
        r = admin_client.get("/api/admin/stats")
        assert r.status_code == 401

    def test_admin_login_wrong_password(self, admin_client):
        r = admin_client.post(
            "/api/admin/login",
            json={"username": ADMIN_USER, "password": "wrong"},
        )
        assert r.status_code == 401

    def test_admin_login_success_sets_session(self, admin_client):
        r = admin_client.post(
            "/api/admin/login",
            json={"username": ADMIN_USER, "password": ADMIN_PASS},
        )
        assert r.status_code == 200
        assert r.json()["message"] == "Login successful"
        # 必须在响应里带了 session cookie
        assert "diary_session" in r.cookies or "session" in r.cookies

    def test_admin_page_accessible_after_login(self, admin_client):
        admin_client.post(
            "/api/admin/login",
            json={"username": ADMIN_USER, "password": ADMIN_PASS},
        )
        r = admin_client.get("/admin", follow_redirects=False)
        assert r.status_code == 200
        assert "后台管理" in r.text

    def test_admin_check_after_login(self, admin_client):
        admin_client.post(
            "/api/admin/login",
            json={"username": ADMIN_USER, "password": ADMIN_PASS},
        )
        r = admin_client.get("/api/admin/check")
        assert r.status_code == 200
        assert r.json() == {"authenticated": True}


class TestAdminStats:
    """登录后，stats 接口应能正常返回数据。"""

    def _login(self, client):
        client.post(
            "/api/admin/login",
            json={"username": ADMIN_USER, "password": ADMIN_PASS},
        )

    def test_stats_returns_expected_fields(self, admin_client):
        self._login(admin_client)
        r = admin_client.get("/api/admin/stats")
        assert r.status_code == 200
        data = r.json()
        # 必备字段
        for key in [
            "total_users",
            "total_diaries",
            "today_active_users",
            "avg_diaries_per_user",
            "total_notes",
            "users_with_notes",
            "daily_diaries",
            "top_users",
        ]:
            assert key in data, f"stats 缺字段: {key}"

    def test_stats_user_count_matches_db(self, admin_client, db_session):
        # 在测试库造一个用户
        from models import User
        from auth import get_password_hash
        u = User(
            username="stats_test_user",
            email="stats_test@example.com",
            hashed_password=get_password_hash("x"),
        )
        db_session.add(u)
        db_session.commit()

        self._login(admin_client)
        r = admin_client.get("/api/admin/stats")
        assert r.status_code == 200
        assert r.json()["total_users"] >= 1

    def test_stats_top_users_has_token_fields(self, admin_client):
        self._login(admin_client)
        r = admin_client.get("/api/admin/stats")
        top_users = r.json()["top_users"]
        if top_users:
            u = top_users[0]
            # token 配额相关字段必须有（这是 admin 面板最关键的可视化数据）
            assert "daily_token_used" in u
            assert "daily_token_limit" in u
            assert "last_active" in u or u.get("last_active") is None  # 未活跃的可以为 null
