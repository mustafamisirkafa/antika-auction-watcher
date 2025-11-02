"""
Team-based access control models for Antika Auction Watcher.
"""
from datetime import datetime
from typing import Optional, List
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship


class MemberRole(str, Enum):
    """Team member roles with hierarchical permissions."""
    OWNER = "OWNER"           # Full control, billing, delete team
    ADMIN = "ADMIN"           # Manage members, agents, settings
    ANALYST = "ANALYST"       # View agents, create reports, limited control
    VIEWER = "VIEWER"         # Read-only access


class PlanCode(str, Enum):
    """Available subscription plans."""
    FREE = "FREE"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


class Team(SQLModel, table=True):
    """
    Team entity. Each team has a plan that defines agent quotas.
    """
    __tablename__ = "teams"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, index=True)
    owner_id: int = Field(foreign_key="users.id", index=True)
    plan_code: str = Field(default="FREE", max_length=20, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    memberships: List["Membership"] = Relationship(back_populates="team")
    usage_records: List["Usage"] = Relationship(back_populates="team")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Acme Antiques Team",
                "owner_id": 1,
                "plan_code": "PRO"
            }
        }


class Membership(SQLModel, table=True):
    """
    Team membership with role-based access control.
    """
    __tablename__ = "memberships"

    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="teams.id", index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    role: str = Field(default="VIEWER", max_length=20, index=True)
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    invited_by: Optional[int] = Field(default=None, foreign_key="users.id")
    
    # Relationships
    team: Team = Relationship(back_populates="memberships")

    class Config:
        json_schema_extra = {
            "example": {
                "team_id": 1,
                "user_id": 2,
                "role": "ANALYST"
            }
        }


class Plan(SQLModel, table=True):
    """
    Subscription plans with agent limits and features.
    Static data, seeded on startup.
    """
    __tablename__ = "plans"

    code: str = Field(primary_key=True, max_length=20)
    agent_limit: int = Field(default=3)
    description: str = Field(max_length=500)
    features: str = Field(default="")  # JSON string of features
    price_monthly: Optional[float] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "code": "PRO",
                "agent_limit": 25,
                "description": "Up to 25 watcher/bidder agents",
                "features": '["advanced_analytics", "priority_support"]',
                "price_monthly": 49.99
            }
        }


class Usage(SQLModel, table=True):
    """
    Usage tracking for teams. Records active agents and daily starts.
    """
    __tablename__ = "usage"

    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="teams.id", index=True)
    active_agents: int = Field(default=0)
    daily_starts: int = Field(default=0)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    
    # Relationships
    team: Team = Relationship(back_populates="usage_records")

    class Config:
        json_schema_extra = {
            "example": {
                "team_id": 1,
                "active_agents": 15,
                "daily_starts": 42,
                "timestamp": "2025-11-02T10:00:00Z"
            }
        }


class AgentConfig(SQLModel, table=True):
    """
    Configuration for individual AI agents (watchers/bidders).
    """
    __tablename__ = "agent_configs"

    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="teams.id", index=True)
    name: str = Field(max_length=100)
    agent_type: str = Field(max_length=50)  # watcher, bidder, analyzer
    status: str = Field(default="stopped", max_length=20)  # running, stopped, paused
    config_json: str = Field(default="{}")  # Agent-specific configuration
    created_by: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_started_at: Optional[datetime] = Field(default=None)
    last_stopped_at: Optional[datetime] = Field(default=None)

    class Config:
        json_schema_extra = {
            "example": {
                "team_id": 1,
                "name": "Ceramics Watcher",
                "agent_type": "watcher",
                "status": "running",
                "config_json": '{"category": "ceramics", "max_bid": 1000}',
                "created_by": 1
            }
        }
