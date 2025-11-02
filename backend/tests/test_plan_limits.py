"""
Test suite for plan limits enforcement (Phase 8).
"""
import pytest
from sqlmodel import Session
import redis.asyncio as redis
from backend.db.models import User
from backend.models.team_models import Team, Membership, AgentConfig, MemberRole
from backend.services.agent_manager import AgentManager
from backend.services.plan_seeder import seed_plans
from fastapi import HTTPException


@pytest.fixture
async def redis_client():
    """Create Redis client for testing."""
    client = redis.Redis.from_url("redis://localhost:6379/15", decode_responses=True)
    await client.flushdb()  # Clean test database
    yield client
    await client.close()


@pytest.fixture
def seed_test_plans(session: Session):
    """Seed plans for testing."""
    seed_plans(session)


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
def free_team(session: Session, test_user: User, seed_test_plans):
    """Create a team with FREE plan (3 agent limit)."""
    team = Team(
        name="Free Team",
        owner_id=test_user.id,
        plan_code="FREE"
    )
    session.add(team)
    session.commit()
    session.refresh(team)
    return team


@pytest.fixture
def pro_team(session: Session, test_user: User, seed_test_plans):
    """Create a team with PRO plan (25 agent limit)."""
    team = Team(
        name="Pro Team",
        owner_id=test_user.id,
        plan_code="PRO"
    )
    session.add(team)
    session.commit()
    session.refresh(team)
    return team


@pytest.mark.asyncio
async def test_can_start_agent_within_limit(
    session: Session,
    redis_client: redis.Redis,
    free_team: Team,
    test_user: User
):
    """Test starting agents within plan limit."""
    manager = AgentManager(redis_client, session)
    
    # Should be able to start 3 agents (FREE plan limit)
    assert await manager.can_start_agent(free_team.id)
    
    # Start first agent
    agent1 = await manager.start_agent(
        free_team.id,
        {"name": "Agent 1", "type": "watcher"},
        test_user.id
    )
    assert agent1.status == "running"
    
    # Should still be able to start more
    assert await manager.can_start_agent(free_team.id)
    
    # Start second agent
    agent2 = await manager.start_agent(
        free_team.id,
        {"name": "Agent 2", "type": "watcher"},
        test_user.id
    )
    assert agent2.status == "running"
    
    # Start third agent (at limit)
    agent3 = await manager.start_agent(
        free_team.id,
        {"name": "Agent 3", "type": "watcher"},
        test_user.id
    )
    assert agent3.status == "running"
    
    # Should NOT be able to start more
    assert not await manager.can_start_agent(free_team.id)


@pytest.mark.asyncio
async def test_cannot_exceed_plan_limit(
    session: Session,
    redis_client: redis.Redis,
    free_team: Team,
    test_user: User
):
    """Test that exceeding plan limit raises error."""
    manager = AgentManager(redis_client, session)
    
    # Start 3 agents (FREE plan limit)
    for i in range(3):
        await manager.start_agent(
            free_team.id,
            {"name": f"Agent {i+1}", "type": "watcher"},
            test_user.id
        )
    
    # Try to start 4th agent - should fail
    with pytest.raises(HTTPException) as exc_info:
        await manager.start_agent(
            free_team.id,
            {"name": "Agent 4", "type": "watcher"},
            test_user.id
        )
    
    assert exc_info.value.status_code == 402
    assert "Plan limit reached" in exc_info.value.detail


@pytest.mark.asyncio
async def test_stop_agent_frees_slot(
    session: Session,
    redis_client: redis.Redis,
    free_team: Team,
    test_user: User
):
    """Test that stopping an agent frees up a slot."""
    manager = AgentManager(redis_client, session)
    
    # Start 3 agents (at limit)
    agents = []
    for i in range(3):
        agent = await manager.start_agent(
            free_team.id,
            {"name": f"Agent {i+1}", "type": "watcher"},
            test_user.id
        )
        agents.append(agent)
    
    # Cannot start more
    assert not await manager.can_start_agent(free_team.id)
    
    # Stop one agent
    await manager.stop_agent(free_team.id, agents[0].id)
    
    # Now can start another
    assert await manager.can_start_agent(free_team.id)
    
    # Start a new agent
    agent4 = await manager.start_agent(
        free_team.id,
        {"name": "Agent 4", "type": "watcher"},
        test_user.id
    )
    assert agent4.status == "running"


@pytest.mark.asyncio
async def test_pro_plan_higher_limit(
    session: Session,
    redis_client: redis.Redis,
    pro_team: Team,
    test_user: User
):
    """Test that PRO plan has higher limit (25 agents)."""
    manager = AgentManager(redis_client, session)
    
    # Start 25 agents (PRO plan limit)
    for i in range(25):
        await manager.start_agent(
            pro_team.id,
            {"name": f"Agent {i+1}", "type": "watcher"},
            test_user.id
        )
    
    # Cannot start more
    assert not await manager.can_start_agent(pro_team.id)
    
    # Verify active count
    active_count = await redis_client.scard(f"team:{pro_team.id}:active_agents")
    assert active_count == 25


@pytest.mark.asyncio
async def test_usage_stats_accurate(
    session: Session,
    redis_client: redis.Redis,
    free_team: Team,
    test_user: User
):
    """Test that usage statistics are accurate."""
    manager = AgentManager(redis_client, session)
    
    # Initial stats
    stats = await manager.get_usage_stats(free_team.id)
    assert stats["active_agents"] == 0
    assert stats["agent_limit"] == 3
    assert stats["available_slots"] == 3
    assert stats["utilization_percent"] == 0
    
    # Start 2 agents
    for i in range(2):
        await manager.start_agent(
            free_team.id,
            {"name": f"Agent {i+1}", "type": "watcher"},
            test_user.id
        )
    
    # Check updated stats
    stats = await manager.get_usage_stats(free_team.id)
    assert stats["active_agents"] == 2
    assert stats["available_slots"] == 1
    assert stats["utilization_percent"] == pytest.approx(66.67, rel=0.1)
    assert stats["daily_starts"] == 2


@pytest.mark.asyncio
async def test_pause_agent_stays_in_active_count(
    session: Session,
    redis_client: redis.Redis,
    free_team: Team,
    test_user: User
):
    """Test that paused agents still count toward limit."""
    manager = AgentManager(redis_client, session)
    
    # Start 3 agents
    agents = []
    for i in range(3):
        agent = await manager.start_agent(
            free_team.id,
            {"name": f"Agent {i+1}", "type": "watcher"},
            test_user.id
        )
        agents.append(agent)
    
    # Pause one agent
    paused_agent = await manager.pause_agent(free_team.id, agents[0].id)
    assert paused_agent.status == "paused"
    
    # Still cannot start more (paused agents count toward limit)
    assert not await manager.can_start_agent(free_team.id)


@pytest.mark.asyncio
async def test_cleanup_stale_agents(
    session: Session,
    redis_client: redis.Redis,
    free_team: Team,
    test_user: User
):
    """Test cleanup of stale Redis entries."""
    manager = AgentManager(redis_client, session)
    
    # Start an agent
    agent = await manager.start_agent(
        free_team.id,
        {"name": "Agent 1", "type": "watcher"},
        test_user.id
    )
    
    # Manually add a stale entry to Redis
    await redis_client.sadd(f"team:{free_team.id}:active_agents", "999999")
    
    # Verify stale entry exists
    count_before = await redis_client.scard(f"team:{free_team.id}:active_agents")
    assert count_before == 2
    
    # Run cleanup
    await manager.cleanup_stale_agents(free_team.id)
    
    # Verify stale entry removed
    count_after = await redis_client.scard(f"team:{free_team.id}:active_agents")
    assert count_after == 1


@pytest.mark.asyncio
async def test_daily_starts_counter(
    session: Session,
    redis_client: redis.Redis,
    free_team: Team,
    test_user: User
):
    """Test daily starts counter increments correctly."""
    manager = AgentManager(redis_client, session)
    from datetime import datetime
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    key = f"team:{free_team.id}:starts:{today}"
    
    # Start 3 agents
    for i in range(3):
        await manager.start_agent(
            free_team.id,
            {"name": f"Agent {i+1}", "type": "watcher"},
            test_user.id
        )
    
    # Check counter
    starts = await redis_client.get(key)
    assert int(starts) == 3
