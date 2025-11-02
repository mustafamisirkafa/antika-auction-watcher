"""
Test suite for Agent Manager service (Phase 8).
"""
import pytest
from sqlmodel import Session
import redis.asyncio as redis
from backend.db.models import User
from backend.models.team_models import Team, AgentConfig
from backend.services.agent_manager import AgentManager
from backend.services.plan_seeder import seed_plans


@pytest.fixture
async def redis_client():
    """Create Redis client for testing."""
    client = redis.Redis.from_url("redis://localhost:6379/15", decode_responses=True)
    await client.flushdb()
    yield client
    await client.close()


@pytest.fixture
def test_user(session: Session):
    """Create a test user."""
    user = User(email="test@example.com", username="testuser", hashed_password="hashed")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture
def test_team(session: Session, test_user: User):
    """Create a test team."""
    seed_plans(session)
    team = Team(name="Test Team", owner_id=test_user.id, plan_code="FREE")
    session.add(team)
    session.commit()
    session.refresh(team)
    return team


@pytest.mark.asyncio
async def test_start_agent(session: Session, redis_client: redis.Redis, test_team: Team, test_user: User):
    """Test starting a new agent."""
    manager = AgentManager(redis_client, session)
    
    agent = await manager.start_agent(
        test_team.id,
        {"name": "Test Agent", "type": "watcher", "category": "ceramics"},
        test_user.id
    )
    
    assert agent.id is not None
    assert agent.name == "Test Agent"
    assert agent.agent_type == "watcher"
    assert agent.status == "running"
    assert agent.team_id == test_team.id
    assert agent.created_by == test_user.id
    assert agent.last_started_at is not None
    
    # Verify Redis entry
    is_active = await redis_client.sismember(f"team:{test_team.id}:active_agents", str(agent.id))
    assert is_active


@pytest.mark.asyncio
async def test_stop_agent(session: Session, redis_client: redis.Redis, test_team: Team, test_user: User):
    """Test stopping an agent."""
    manager = AgentManager(redis_client, session)
    
    # Start agent
    agent = await manager.start_agent(
        test_team.id,
        {"name": "Test Agent", "type": "watcher"},
        test_user.id
    )
    
    # Stop agent
    stopped_agent = await manager.stop_agent(test_team.id, agent.id)
    
    assert stopped_agent.status == "stopped"
    assert stopped_agent.last_stopped_at is not None
    
    # Verify Redis entry removed
    is_active = await redis_client.sismember(f"team:{test_team.id}:active_agents", str(agent.id))
    assert not is_active


@pytest.mark.asyncio
async def test_get_active_agents(session: Session, redis_client: redis.Redis, test_team: Team, test_user: User):
    """Test getting all active agents."""
    manager = AgentManager(redis_client, session)
    
    # Start 2 agents
    agent1 = await manager.start_agent(test_team.id, {"name": "Agent 1", "type": "watcher"}, test_user.id)
    agent2 = await manager.start_agent(test_team.id, {"name": "Agent 2", "type": "bidder"}, test_user.id)
    
    # Stop one
    await manager.stop_agent(test_team.id, agent1.id)
    
    # Get active agents
    active_agents = await manager.get_active_agents(test_team.id)
    
    assert len(active_agents) == 1
    assert active_agents[0].id == agent2.id


@pytest.mark.asyncio
async def test_get_agent_by_id(session: Session, redis_client: redis.Redis, test_team: Team, test_user: User):
    """Test getting agent by ID."""
    manager = AgentManager(redis_client, session)
    
    agent = await manager.start_agent(test_team.id, {"name": "Test Agent", "type": "watcher"}, test_user.id)
    
    retrieved_agent = await manager.get_agent_by_id(test_team.id, agent.id)
    
    assert retrieved_agent is not None
    assert retrieved_agent.id == agent.id
    assert retrieved_agent.name == "Test Agent"


@pytest.mark.asyncio
async def test_get_usage_stats(session: Session, redis_client: redis.Redis, test_team: Team, test_user: User):
    """Test getting usage statistics."""
    manager = AgentManager(redis_client, session)
    
    # Start 2 agents
    await manager.start_agent(test_team.id, {"name": "Agent 1", "type": "watcher"}, test_user.id)
    await manager.start_agent(test_team.id, {"name": "Agent 2", "type": "watcher"}, test_user.id)
    
    stats = await manager.get_usage_stats(test_team.id)
    
    assert stats["team_id"] == test_team.id
    assert stats["plan_code"] == "FREE"
    assert stats["agent_limit"] == 3
    assert stats["active_agents"] == 2
    assert stats["available_slots"] == 1
    assert stats["daily_starts"] == 2
    assert stats["total_agents"] == 2
    assert stats["utilization_percent"] == pytest.approx(66.67, rel=0.1)


@pytest.mark.asyncio
async def test_agent_config_json(session: Session, redis_client: redis.Redis, test_team: Team, test_user: User):
    """Test that agent configuration is stored correctly."""
    manager = AgentManager(redis_client, session)
    
    config = {
        "name": "Ceramics Watcher",
        "type": "watcher",
        "category": "ceramics",
        "max_bid": 1000,
        "auto_bid": False,
        "filters": {
            "min_age": 50,
            "condition": "excellent"
        }
    }
    
    agent = await manager.start_agent(test_team.id, config, test_user.id)
    
    import json
    stored_config = json.loads(agent.config_json)
    
    assert stored_config["category"] == "ceramics"
    assert stored_config["max_bid"] == 1000
    assert stored_config["filters"]["min_age"] == 50


@pytest.mark.asyncio
async def test_pause_agent(session: Session, redis_client: redis.Redis, test_team: Team, test_user: User):
    """Test pausing an agent."""
    manager = AgentManager(redis_client, session)
    
    agent = await manager.start_agent(test_team.id, {"name": "Test Agent", "type": "watcher"}, test_user.id)
    
    paused_agent = await manager.pause_agent(test_team.id, agent.id)
    
    assert paused_agent.status == "paused"
    
    # Paused agents should still be in active set
    is_active = await redis_client.sismember(f"team:{test_team.id}:active_agents", str(agent.id))
    assert is_active
    
    # Should still count toward active agents
    active_agents = await manager.get_active_agents(test_team.id)
    assert len(active_agents) == 1
