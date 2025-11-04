"""
Redis Sentinel Client (Sprint 1)
Provides high-availability Redis connection with automatic failover.
"""
import logging
from typing import Optional, List
from redis.sentinel import Sentinel
from redis.asyncio import Redis
from redis import ConnectionError

logger = logging.getLogger(__name__)


class RedisSentinelManager:
    """
    Manages Redis connection with Sentinel support.
    Provides automatic failover to replica nodes.
    """
    
    def __init__(
        self,
        sentinel_hosts: List[tuple] = None,
        master_name: str = "mymaster",
        password: Optional[str] = None,
        db: int = 0,
    ):
        """
        Initialize Redis Sentinel manager.
        
        Args:
            sentinel_hosts: List of (host, port) tuples for sentinels
            master_name: Name of the Redis master in Sentinel config
            password: Redis password (if auth enabled)
            db: Redis database number
        """
        # Default sentinel hosts
        if sentinel_hosts is None:
            sentinel_hosts = [
                ("redis-sentinel-1", 26379),
                ("redis-sentinel-2", 26379),
                ("redis-sentinel-3", 26379),
            ]
        
        self.sentinel_hosts = sentinel_hosts
        self.master_name = master_name
        self.password = password
        self.db = db
        self.sentinel: Optional[Sentinel] = None
        self.master_client: Optional[Redis] = None
        self.slave_client: Optional[Redis] = None
    
    async def connect(self) -> None:
        """
        Connect to Redis via Sentinel.
        Discovers master and creates client connections.
        """
        try:
            # Create Sentinel instance
            self.sentinel = Sentinel(
                self.sentinel_hosts,
                socket_timeout=0.1,
                password=self.password,
            )
            
            # Discover master
            master_address = self.sentinel.discover_master(self.master_name)
            logger.info(f"Redis master discovered at {master_address}")
            
            # Get master client
            self.master_client = self.sentinel.master_for(
                self.master_name,
                socket_timeout=0.1,
                password=self.password,
                db=self.db,
            )
            
            # Get slave client (for read operations)
            self.slave_client = self.sentinel.slave_for(
                self.master_name,
                socket_timeout=0.1,
                password=self.password,
                db=self.db,
            )
            
            # Test connection
            await self.master_client.ping()
            logger.info("Redis Sentinel connection established")
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis Sentinel: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connections."""
        try:
            if self.master_client:
                await self.master_client.close()
            if self.slave_client:
                await self.slave_client.close()
            logger.info("Redis Sentinel connections closed")
        except Exception as e:
            logger.error(f"Error closing Redis connections: {e}")
    
    def get_master(self) -> Redis:
        """
        Get master Redis client (for write operations).
        
        Returns:
            Redis client connected to current master
        
        Raises:
            ConnectionError: If not connected
        """
        if not self.master_client:
            raise ConnectionError("Not connected to Redis Sentinel")
        return self.master_client
    
    def get_slave(self) -> Redis:
        """
        Get slave Redis client (for read operations).
        
        Returns:
            Redis client connected to a slave
        
        Raises:
            ConnectionError: If not connected
        """
        if not self.slave_client:
            raise ConnectionError("Not connected to Redis Sentinel")
        return self.slave_client
    
    async def is_healthy(self) -> bool:
        """
        Check if Redis connection is healthy.
        
        Returns:
            True if master is reachable
        """
        try:
            if self.master_client:
                await self.master_client.ping()
                return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
        return False
    
    def get_sentinel_info(self) -> dict:
        """
        Get Sentinel cluster information.
        
        Returns:
            Dict with master info and sentinel states
        """
        if not self.sentinel:
            return {"error": "Not connected to Sentinel"}
        
        try:
            master_info = self.sentinel.discover_master(self.master_name)
            slaves_info = self.sentinel.discover_slaves(self.master_name)
            
            return {
                "master": {
                    "host": master_info[0],
                    "port": master_info[1],
                },
                "slaves": [
                    {"host": slave[0], "port": slave[1]}
                    for slave in slaves_info
                ],
                "sentinels": [
                    {"host": host, "port": port}
                    for host, port in self.sentinel_hosts
                ],
            }
        except Exception as e:
            logger.error(f"Error getting Sentinel info: {e}")
            return {"error": str(e)}
