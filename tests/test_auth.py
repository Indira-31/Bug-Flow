from app.auth import verify_password

def test_user_registration(client):
    payload = {
        "username": "new_engineer",
        "email": "engineer@company.com",
        "password": "SecurePassword123!",
        "full_name": "New Engineer",
        "role": "DEVELOPER",
        "team": "Core Dev",
        "core_skills": "Python, SQL",
        "proficiency": "Senior"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "new_engineer"
    assert data["email"] == "engineer@company.com"
    assert data["role"] == "DEVELOPER"
    assert "password" not in data
    assert "hashed_password" not in data

def test_duplicate_registration_rejected(client):
    payload = {
        "username": "admin_user",  # Already in seed
        "email": "another@test.io",
        "password": "password123",
        "full_name": "Duplicate Admin"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]

def test_login_success(client):
    response = client.post("/api/v1/auth/login", json={
        "username": "admin_user",
        "password": "testpass123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin_user"
    assert data["user"]["role"] == "ADMIN"

def test_login_invalid_credentials(client):
    response = client.post("/api/v1/auth/login", json={
        "username": "admin_user",
        "password": "WrongPassword!"
    })
    assert response.status_code == 401
    assert "Invalid username/email or password" in response.json()["detail"]

def test_get_current_user_profile(client, dev_headers):
    response = client.get("/api/v1/auth/me", headers=dev_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "john_dev"
    assert data["role"] == "DEVELOPER"

def test_unauthorized_access(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401

def test_rbac_project_creation_permission(client, admin_headers, stakeholder_headers):
    # ADMIN should succeed
    res_admin = client.post("/api/v1/projects/", json={
        "project_name": "RBAC Allowed Project",
        "codebase": "github.com/test/rbac"
    }, headers=admin_headers)
    assert res_admin.status_code == 201

    # STAKEHOLDER should be forbidden (403)
    res_stakeholder = client.post("/api/v1/projects/", json={
        "project_name": "RBAC Forbidden Project",
        "codebase": "github.com/test/rbac2"
    }, headers=stakeholder_headers)
    assert res_stakeholder.status_code == 403
