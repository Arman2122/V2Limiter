"""
Redis utilities for storing and retrieving connected IP addresses.
"""

import json
import time
import redis
from typing import Dict, List, Optional, Set, Any, Union

from utils.logs import logger
from utils.read_config import read_config


class RedisClient:
    """Redis client for storing and retrieving IP addresses."""
    
    _instance = None
    
    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    async def initialize(self):
        """Initialize Redis connection."""
        if self._initialized:
            return
        
        config = await read_config()
        redis_host = config.get("REDIS_HOST", "localhost")
        redis_port = config.get("REDIS_PORT", 6379)
        redis_db = config.get("REDIS_DB", 0)
        redis_password = config.get("REDIS_PASSWORD", None)
        
        try:
            self.redis = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=True  # Return strings instead of bytes
            )
            logger.info(f"Connected to Redis at {redis_host}:{redis_port} DB:{redis_db}")
            self._initialized = True
            
            # Initialize last_update_timestamp if it doesn't exist
            if not self.redis.exists("last_update_timestamp"):
                self.redis.set("last_update_timestamp", int(time.time()))
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def add_ip_to_service(self, service_name: str, ip_address: str) -> bool:
        """
        Add an IP address to a service.
        
        Args:
            service_name: The name of the service
            ip_address: The IP address to add
            
        Returns:
            bool: True if added successfully, False otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            ip_data = self.redis.hget("service_ips", service_name)
            if ip_data:
                ip_set = set(json.loads(ip_data))
            else:
                ip_set = set()
            
            ip_set.add(ip_address)
            
            self.redis.hset("service_ips", service_name, json.dumps(list(ip_set)))
            
            logger.debug(f"Added IP {ip_address} to service {service_name}")
            return True
        except Exception as e:
            logger.error(f"Error adding IP to Redis: {e}")
            return False
    
    async def remove_ip_from_service(self, service_name: str, ip_address: str) -> bool:
        """
        Remove an IP address from a service.
        
        Args:
            service_name: The name of the service
            ip_address: The IP address to remove
            
        Returns:
            bool: True if removed successfully, False otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            ip_data = self.redis.hget("service_ips", service_name)
            if not ip_data:
                return False
            
            ip_set = set(json.loads(ip_data))
            if ip_address in ip_set:
                ip_set.remove(ip_address)
                
                if ip_set:
                    self.redis.hset("service_ips", service_name, json.dumps(list(ip_set)))
                else:
                    self.redis.hdel("service_ips", service_name)
                
                logger.debug(f"Removed IP {ip_address} from service {service_name}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error removing IP from Redis: {e}")
            return False
    
    async def get_service_ips(self, service_name: str) -> List[str]:
        """
        Get all IP addresses for a service.
        
        Args:
            service_name: The name of the service
            
        Returns:
            List[str]: List of IP addresses
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            ip_data = self.redis.hget("service_ips", service_name)
            if ip_data:
                return json.loads(ip_data)
            return []
        except Exception as e:
            logger.error(f"Error getting IPs for service from Redis: {e}")
            return []
    
    async def get_all_service_ips(self) -> Dict[str, Union[Dict[str, List[str]], int]]:
        """
        Get all services and their IPs with a single last_update timestamp.
        
        Returns:
            Dict: Dictionary with services and a global last_update timestamp
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            result = {}
            services = {}
            
            # Get all services and their IPs
            service_keys = self.redis.hkeys("service_ips")
            
            for service in service_keys:
                ip_data = self.redis.hget("service_ips", service)
                if ip_data:
                    ips = json.loads(ip_data)
                    services[service] = ips
            
            # Get the global last update timestamp
            last_update = self.redis.get("last_update_timestamp")
            last_update = int(last_update) if last_update else int(time.time())
            
            result = {
                "services": services,
                "last_update": last_update
            }
            
            return result
        except Exception as e:
            logger.error(f"Error getting all services and IPs from Redis: {e}")
            return {"services": {}, "last_update": int(time.time())}
    
    # New methods for handling special limits
    async def set_special_limits(self, special_limits: Dict[str, int]) -> bool:
        """
        Store special limits in Redis.
        
        Args:
            special_limits: Dict of username to limit
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            self.redis.set("special_limits", json.dumps(special_limits))
            logger.info(f"Updated special limits in Redis: {special_limits}")
            return True
        except Exception as e:
            logger.error(f"Error setting special limits in Redis: {e}")
            return False
    
    # New methods for handling except users
    async def set_except_users(self, except_users: List[str]) -> bool:
        """
        Store except users in Redis.
        
        Args:
            except_users: List of usernames to exempt
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            self.redis.set("except_users", json.dumps(except_users))
            logger.info(f"Updated except users in Redis: {except_users}")
            return True
        except Exception as e:
            logger.error(f"Error setting except users in Redis: {e}")
            return False
    
    async def get_except_users(self) -> List[str]:
        """
        Get except users from Redis.
        
        Returns:
            List[str]: List of exempt usernames
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            users_data = self.redis.get("except_users")
            if users_data:
                return json.loads(users_data)
            return []
        except Exception as e:
            logger.error(f"Error getting except users from Redis: {e}")
            return []
    
    async def add_except_user(self, username: str) -> bool:
        """
        Add a user to the exception list.
        
        Args:
            username: The username to exempt
            
        Returns:
            bool: True if added successfully, False otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Get current except users
            users = await self.get_except_users()
            
            # Add the user if not already in the list
            if username not in users:
                users.append(username)
                
                # Store the updated list
                return await self.set_except_users(users)
            return True  # User already exists in the list
        except Exception as e:
            logger.error(f"Error adding except user to Redis: {e}")
            return False
    
    async def remove_except_user(self, username: str) -> bool:
        """
        Remove a user from the exception list.
        
        Args:
            username: The username to remove
            
        Returns:
            bool: True if removed successfully, False otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Get current except users
            users = await self.get_except_users()
            
            # Remove the user if exists
            if username in users:
                users.remove(username)
                
                # Store the updated list
                return await self.set_except_users(users)
            return False  # User not in the list
        except Exception as e:
            logger.error(f"Error removing except user from Redis: {e}")
            return False
    
    async def get_special_limits(self) -> Dict[str, int]:
        """
        Get special limits from Redis.
        
        Returns:
            Dict[str, int]: Dict of username to limit
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            limits_data = self.redis.get("special_limits")
            if limits_data:
                return json.loads(limits_data)
            return {}
        except Exception as e:
            logger.error(f"Error getting special limits from Redis: {e}")
            return {}
    
    async def add_special_limit(self, username: str, limit: int) -> bool:
        """
        Add a special limit for a user.
        
        Args:
            username: The username
            limit: The limit value
            
        Returns:
            bool: True if added successfully, False otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Get current special limits
            limits = await self.get_special_limits()
            
            # Add or update the limit
            limits[username] = limit
            
            # Store the updated limits
            return await self.set_special_limits(limits)
        except Exception as e:
            logger.error(f"Error adding special limit to Redis: {e}")
            return False
    
    async def remove_special_limit(self, username: str) -> bool:
        """
        Remove a special limit for a user.
        
        Args:
            username: The username to remove
            
        Returns:
            bool: True if removed successfully, False otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Get current special limits
            limits = await self.get_special_limits()
            
            # Remove the user if exists
            if username in limits:
                del limits[username]
                
                # Store the updated limits
                return await self.set_special_limits(limits)
            return False
        except Exception as e:
            logger.error(f"Error removing special limit from Redis: {e}")
            return False
    
    async def clear_all_data(self) -> bool:
        """
        Clear all Redis data related to services and IPs.
        Also updates the last_update timestamp.
        
        Returns:
            bool: True if cleared successfully, False otherwise
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # Delete main service_ips hash
            self.redis.delete("service_ips")
            
            # Update the last update timestamp - this is the only place where last_update should be updated
            timestamp = int(time.time())
            self.redis.set("last_update_timestamp", timestamp)
            
            logger.info(f"Cleared all Redis data for services and IPs. Last update timestamp set to {timestamp}")
            return True
        except Exception as e:
            logger.error(f"Error clearing Redis data: {e}")
            return False

# Create a singleton instance
redis_client = RedisClient() 