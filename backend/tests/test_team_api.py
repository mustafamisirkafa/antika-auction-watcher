"""
Test suite for team management API (Phase 8).
"""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
from backend.db.models import User
from backend.models.team_models import Team, Membership, Plan, MemberRole
from backend.services.plan_seeder import seed_plans


@pytest.fixture
def seed_test_plans(session: Session):
    """Seed plans for testing."""
    seed_plans(session)
    yield
    # Cleanup done by fixture


@pytest.fixture
def test_user(session: Session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password="hashed_password"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def test_user2(session: Session):
    """Create a second test user."""
    user = User(
        email="test2@example.com",
        username="testuser2",
        hashed_password="hashed_password"
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def test_team(session: Session, test_user: User):
    """Create a test team with owner membership."""
    team = Team(
        name="Test Team",
        owner_id=test_user.id,
        plan_code="FREE"
    )
    session.add(team)
    session.commit()
    session.refresh(team)
    
    # Add owner membership
    membership = Membership(
        team_id=team.id,
        user_id=test_user.id,
        role=MemberRole.OWNER
    )
    session.add(membership)
    session.commit()
    
    return team


def test_create_team(client: TestClient, test_user: User, seed_test_plans):
    """Test team creation."""
    response = client.post(
        "/api/v1/teams",
        json={"name": "New Team", "plan_code": "PRO"},
        headers={"Authorization": f"Bearer fake_token_for_{test_user.id}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Team"
    assert data["plan_code"] == "PRO"
    assert data["owner_id"] == test_user.id
    assert data["member_count"] == 1


def test_create_team_invalid_plan(client: TestClient, test_user: User):
    """Test team creation with invalid plan code."""
    response = client.post(
        "/api/v1/teams",
        json={"name": "New Team", "plan_code": "INVALID"},
        headers={"Authorization": f"Bearer fake_token_for_{test_user.id}"}
    )
    
    assert response.status_code == 400
    assert "Invalid plan code" in response.json()["detail"]


def test_list_teams(client: TestClient, test_user: User, test_team: Team):
    """Test listing user's teams."""
    response = client.get(
        "/api/v1/teams",
        headers={"Authorization": f"Bearer fake_token_for_{test_user.id}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(team["id"] == test_team.id for team in data)


def test_get_team(client: TestClient, test_user: User, test_team: Team):
    """Test getting team details."""
    response = client.get(
        f"/api/v1/teams/{test_team.id}",
        headers={
            "Authorization": f"Bearer fake_token_for_{test_user.id}",
            "X-Team-Id": str(test_team.id)
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == test_team.id
    assert data["name"] == test_team.name


def test_get_team_not_member(client: TestClient, test_user2: User, test_team: Team):
    """Test getting team details when not a member."""
    response = client.get(
        f"/api/v1/teams/{test_team.id}",
        headers={
            "Authorization": f"Bearer fake_token_for_{test_user2.id}",
            "X-Team-Id": str(test_team.id)
        }
    )
    
    assert response.status_code == 403


def test_list_team_members(client: TestClient, test_user: User, test_team: Team):
    """Test listing team members."""
    response = client.get(
        f"/api/v1/teams/{test_team.id}/members",
        headers={
            "Authorization": f"Bearer fake_token_for_{test_user.id}",
            "X-Team-Id": str(test_team.id)
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["user_id"] == test_user.id
    assert data[0]["role"] == MemberRole.OWNER


def test_add_team_member(
    client: TestClient,
    session: Session,
    test_user: User,
    test_user2: User,
    test_team: Team
):
    """Test adding a member to a team."""
    response = client.post(
        f"/api/v1/teams/{test_team.id}/members",
        json={"user_id": test_user2.id, "role": "ANALYST"},
        headers={
            "Authorization": f"Bearer fake_token_for_{test_user.id}",
            "X-Team-Id": str(test_team.id)
        }
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == test_user2.id
    assert data["role"] == "ANALYST"


def test_add_team_member_non_admin(
    client: TestClient,
    session: Session,
    test_user: User,
    test_user2: User,
    test_team: Team
):
    """Test adding member without admin permissions."""
    # Add test_user2 as VIEWER
    membership = Membership(
        team_id=test_team.id,
        user_id=test_user2.id,
        role=MemberRole.VIEWER
    )
    session.add(membership)
    session.commit()
    
    # Create another user to add
    user3 = User(
        email="test3@example.com",
        username="testuser3",
        hashed_password="hashed"
    )
    session.add(user3)
    session.commit()
    session.refresh(user3)
    
    response = client.post(
        f"/api/v1/teams/{test_team.id}/members",
        json={"user_id": user3.id, "role": "VIEWER"},
        headers={
            "Authorization": f"Bearer fake_token_for_{test_user2.id}",
            "X-Team-Id": str(test_team.id)
        }
    )
    
    assert response.status_code == 403


def test_update_member_role(
    client: TestClient,
    session: Session,
    test_user: User,
    test_user2: User,
    test_team: Team
):
    """Test updating a member's role."""
    # Add test_user2 as VIEWER
    membership = Membership(
        team_id=test_team.id,
        user_id=test_user2.id,
        role=MemberRole.VIEWER
    )
    session.add(membership)
    session.commit()
    
    response = client.patch(
        f"/api/v1/teams/{test_team.id}/members/{test_user2.id}",
        json={"role": "ANALYST"},
        headers={
            "Authorization": f"Bearer fake_token_for_{test_user.id}",
            "X-Team-Id": str(test_team.id)
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "ANALYST"


def test_update_owner_role_forbidden(
    client: TestClient,
    test_user: User,
    test_team: Team
):
    """Test that updating owner role is forbidden."""
    response = client.patch(
        f"/api/v1/teams/{test_team.id}/members/{test_user.id}",
        json={"role": "ADMIN"},
        headers={
            "Authorization": f"Bearer fake_token_for_{test_user.id}",
            "X-Team-Id": str(test_team.id)
        }
    )
    
    assert response.status_code == 400
    assert "Cannot change owner role" in response.json()["detail"]


def test_remove_team_member(
    client: TestClient,
    session: Session,
    test_user: User,
    test_user2: User,
    test_team: Team
):
    """Test removing a member from a team."""
    # Add test_user2 as VIEWER
    membership = Membership(
        team_id=test_team.id,
        user_id=test_user2.id,
        role=MemberRole.VIEWER
    )
    session.add(membership)
    session.commit()
    
    response = client.delete(
        f"/api/v1/teams/{test_team.id}/members/{test_user2.id}",
        headers={
            "Authorization": f"Bearer fake_token_for_{test_user.id}",
            "X-Team-Id": str(test_team.id)
        }
    )
    
    assert response.status_code == 204


def test_remove_owner_forbidden(
    client: TestClient,
    test_user: User,
    test_team: Team
):
    """Test that removing owner is forbidden."""
    response = client.delete(
        f"/api/v1/teams/{test_team.id}/members/{test_user.id}",
        headers={
            "Authorization": f"Bearer fake_token_for_{test_user.id}",
            "X-Team-Id": str(test_team.id)
        }
    )
    
    assert response.status_code == 400
    assert "Cannot remove team owner" in response.json()["detail"]


def test_team_context_missing_header(client: TestClient, test_user: User, test_team: Team):
    """Test that X-Team-Id header is required."""
    response = client.get(
        f"/api/v1/teams/{test_team.id}",
        headers={"Authorization": f"Bearer fake_token_for_{test_user.id}"}
    )
    
    assert response.status_code == 400
    assert "X-Team-Id header required" in response.json()["detail"]


def test_team_context_invalid_team_id(client: TestClient, test_user: User):
    """Test with invalid team ID."""
    response = client.get(
        f"/api/v1/teams/999999",
        headers={
            "Authorization": f"Bearer fake_token_for_{test_user.id}",
            "X-Team-Id": "999999"
        }
    )
    
    assert response.status_code == 404
