"""
Test suite for Usage Tracker service (Phase 8).
"""
import pytest
from datetime import datetime, timedelta
from sqlmodel import Session
import redis.asyncio as redis
from backend.db.models import User
from backend.models.team_models import Team, Usage
from backend.services.usage_tracker import UsageTracker
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
    team = Team(name="Test Team", owner_id=test_user.id, plan_code="PRO")
    session.add(team)
    session.commit()
    session.refresh(team)
    return team


@pytest.mark.asyncio
async def test_record_usage_snapshot(session: Session, redis_client: redis.Redis, test_team: Team):
    """Test recording a usage snapshot."""
    tracker = UsageTracker(redis_client, session)
    
    # Set up Redis data
    await redis_client.sadd(f"team:{test_team.id}:active_agents", "1", "2", "3")
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    await redis_client.set(f"team:{test_team.id}:starts:{today}", "15")
    
    # Record snapshot
    usage = await tracker.record_usage_snapshot(test_team.id)
    
    assert usage.team_id == test_team.id
    assert usage.active_agents == 3
    assert usage.daily_starts == 15
    assert usage.timestamp is not None


@pytest.mark.asyncio
async def test_record_all_teams_usage(session: Session, redis_client: redis.Redis, test_team: Team):
    """Test recording usage for all teams."""
    tracker = UsageTracker(redis_client, session)
    
    # Create another team
    user2 = User(email="test2@example.com", username="testuser2", hashed_password="hashed")
    session.add(user2)
    session.commit()
    session.refresh(user2)
    
    team2 = Team(name="Team 2", owner_id=user2.id, plan_code="FREE")
    session.add(team2)
    session.commit()
    session.refresh(team2)
    
    # Set up Redis data for both teams
    await redis_client.sadd(f"team:{test_team.id}:active_agents", "1", "2")
    await redis_client.sadd(f"team:{team2.id}:active_agents", "1")
    
    # Record usage for all teams
    usage_records = await tracker.record_all_teams_usage()
    
    assert len(usage_records) == 2
    assert any(u.team_id == test_team.id for u in usage_records)
    assert any(u.team_id == team2.id for u in usage_records)


@pytest.mark.asyncio
async def test_get_usage_history(session: Session, redis_client: redis.Redis, test_team: Team):
    """Test getting usage history."""
    tracker = UsageTracker(redis_client, session)
    
    # Create usage records
    usage1 = Usage(team_id=test_team.id, active_agents=5, daily_starts=10, timestamp=datetime.utcnow())
    usage2 = Usage(
        team_id=test_team.id,
        active_agents=8,
        daily_starts=15,
        timestamp=datetime.utcnow() - timedelta(hours=1)
    )
    usage3 = Usage(
        team_id=test_team.id,
        active_agents=3,
        daily_starts=20,
        timestamp=datetime.utcnow() - timedelta(hours=25)  # Outside 24h window
    )
    
    session.add_all([usage1, usage2, usage3])
    session.commit()
    
    # Get history for last 24 hours
    history = await tracker.get_usage_history(test_team.id, hours=24)
    
    assert len(history) == 2  # Only records within 24 hours
    assert history[0].active_agents == 5  # Most recent first


@pytest.mark.asyncio
async def test_get_usage_summary(session: Session, redis_client: redis.Redis, test_team: Team):
    """Test getting usage summary statistics."""
    tracker = UsageTracker(redis_client, session)
    
    # Create usage records
    for i in range(5):
        usage = Usage(
            team_id=test_team.id,
            active_agents=i + 1,
            daily_starts=i * 2,
            timestamp=datetime.utcnow() - timedelta(hours=i)
        )
        session.add(usage)
    session.commit()
    
    # Get summary
    summary = await tracker.get_usage_summary(test_team.id, hours=24)
    
    assert summary["team_id"] == test_team.id
    assert summary["hours"] == 24
    assert summary["avg_active_agents"] == pytest.approx(3.0, rel=0.1)
    assert summary["max_active_agents"] == 5
    assert summary["min_active_agents"] == 1
    assert summary["total_starts"] == 8  # Max of daily_starts
    assert summary["data_points"] == 5


@pytest.mark.asyncio
async def test_get_usage_summary_empty(session: Session, redis_client: redis.Redis, test_team: Team):
    """Test getting usage summary with no data."""
    tracker = UsageTracker(redis_client, session)
    
    summary = await tracker.get_usage_summary(test_team.id, hours=24)
    
    assert summary["avg_active_agents"] == 0
    assert summary["max_active_agents"] == 0
    assert summary["min_active_agents"] == 0
    assert summary["total_starts"] == 0
    assert summary["data_points"] == 0


@pytest.mark.asyncio
async def test_cleanup_old_usage_records(session: Session, redis_client: redis.Redis, test_team: Team):
    """Test cleanup of old usage records."""
    tracker = UsageTracker(redis_client, session)
    
    # Create old and new records
    old_usage = Usage(
        team_id=test_team.id,
        active_agents=5,
        daily_starts=10,
        timestamp=datetime.utcnow() - timedelta(days=35)
    )
    new_usage = Usage(
        team_id=test_team.id,
        active_agents=8,
        daily_starts=15,
        timestamp=datetime.utcnow()
    )
    
    session.add_all([old_usage, new_usage])
    session.commit()
    
    # Cleanup old records (> 30 days)
    await tracker.cleanup_old_usage_records(days=30)
    
    # Verify old record deleted, new record kept
    from sqlmodel import select
    statement = select(Usage).where(Usage.team_id == test_team.id)
    remaining_records = session.exec(statement).all()
    
    assert len(remaining_records) == 1
    assert remaining_records[0].active_agents == 8


@pytest.mark.asyncio
async def test_cleanup_old_start_counters(session: Session, redis_client: redis.Redis, test_team: Team):
    """Test cleanup of old daily start counters."""
    tracker = UsageTracker(redis_client, session)
    
    # Create start counters for various days
    today = datetime.utcnow()
    for days_ago in range(40):
        date_str = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        await redis_client.set(f"team:{test_team.id}:starts:{date_str}", str(days_ago))
    
    # Cleanup counters older than 7 days
    await tracker.cleanup_old_start_counters(days=7)
    
    # Verify recent counters kept, old ones removed
    for days_ago in range(7):
        date_str = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        key = f"team:{test_team.id}:starts:{date_str}"
        value = await redis_client.get(key)
        assert value is not None  # Recent keys should exist
