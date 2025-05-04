"""
This module contains functions to parse and validate logs.
"""

import ipaddress
import random
import re
import sys
import time
import json
import os
from typing import Dict, Any, Optional

from utils.check_usage import ACTIVE_USERS
from utils.read_config import read_config
from utils.types import UserType
from utils.redis_utils import redis_client
from utils.logs import logger

try:
    import httpx
except ImportError:
    print("Module 'httpx' is not installed use: 'pip install httpx' to install it")
    sys.exit()

INVALID_EMAILS = [
    "API]",
    "Found",
    "(normal)",
    "timeout",
    "EOF",
    "address",
    "INFO",
    "request",
]
INVALID_IPS = {
    "1.1.1.1",
    "8.8.8.8",
}
VALID_IPS = []
CACHE = {}

# IP location cache configuration
CACHE_FILE = "ip_location_cache.json"
CACHE_TTL = 3 * 24 * 60 * 60  # 3 days in seconds

API_ENDPOINTS = {
    "https://api.iplocation.net/?ip={ip}": "country_code2",
    "http://ip-api.com/json/{ip}": "countryCode",
    "https://ipinfo.io/{ip}/json": "country",
    "https://ipwhois.app/json/{ip}": "country_code",
}


async def remove_id_from_username(username: str) -> str:
    """
    Remove the ID from the start of the username.
    Args:
        username (str): The username string from which to remove the ID.

    Returns:
        str: The username with the ID removed.
    """
    return re.sub(r"^\d+\.", "", username)


def load_ip_cache() -> Dict[str, Dict[str, Any]]:
    """
    Load the IP location cache from file.
    
    Returns:
        Dict[str, Dict[str, Any]]: The loaded cache
    """
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
                logger.info(f"Loaded IP location cache with {len(cache_data)} entries")
                return cache_data
    except Exception as e:
        logger.error(f"Error loading IP cache: {e}")
    
    return {}


def save_ip_cache(cache: Dict[str, Dict[str, Any]]) -> None:
    """
    Save the IP location cache to file.
    
    Args:
        cache (Dict[str, Dict[str, Any]]): The cache to save
    """
    try:
        # Remove expired entries before saving
        current_time = time.time()
        clean_cache = {
            ip: data for ip, data in cache.items() 
            if current_time - data.get("timestamp", 0) < CACHE_TTL
        }
        
        # Save to file
        with open(CACHE_FILE, 'w') as f:
            json.dump(clean_cache, f)
        
        logger.info(f"Saved IP location cache with {len(clean_cache)} entries")
    except Exception as e:
        logger.error(f"Error saving IP cache: {e}")


# Initialize the IP cache
IP_CACHE = load_ip_cache()


async def check_ip(ip_address: str) -> Optional[str]:
    """
    Check the geographical location of an IP address.

    Get the location of the IP address using multiple APIs with fallback.
    Uses a persistent cache with 3-day TTL to avoid unnecessary requests.

    Args:
        ip_address (str): The IP address to check.

    Returns:
        str: The country code of the IP address location, or None
    """
    global IP_CACHE
    
    # Check in-memory cache first
    if ip_address in CACHE:
        logger.debug(f"IP {ip_address} found in memory cache")
        return CACHE[ip_address]
    
    # Check persistent cache
    current_time = time.time()
    if ip_address in IP_CACHE:
        cache_entry = IP_CACHE[ip_address]
        # Check if the cache entry is still valid
        if current_time - cache_entry.get("timestamp", 0) < CACHE_TTL:
            country_code = cache_entry.get("country_code")
            if country_code:
                logger.debug(f"IP {ip_address} found in persistent cache: {country_code}")
                # Update in-memory cache
                CACHE[ip_address] = country_code
                return country_code
    
    # Create a randomized list of endpoints to try
    endpoints = list(API_ENDPOINTS.items())
    random.shuffle(endpoints)
    
    logger.info(f"Looking up location for IP: {ip_address}")
    
    for endpoint, key in endpoints:
        endpoint_name = endpoint.split("//")[1].split("/")[0]
        url = endpoint.replace("{ip}", ip_address)
        
        try:
            logger.debug(f"Trying endpoint {endpoint_name} for IP {ip_address}")
            async with httpx.AsyncClient(verify=False) as client:
                resp = await client.get(url, timeout=3)
                
            # Check if the request was successful
            if resp.status_code != 200:
                logger.warning(f"API {endpoint_name} returned status {resp.status_code} for IP {ip_address}")
                continue
                
            # Parse the response based on the API
            try:
                info = resp.json()
                country = info.get(key)
                
                if country:
                    logger.info(f"IP {ip_address} location found: {country} (via {endpoint_name})")
                    
                    # Update in-memory cache
                    CACHE[ip_address] = country
                    
                    # Update persistent cache
                    IP_CACHE[ip_address] = {
                        "country_code": country,
                        "timestamp": current_time,
                        "source": endpoint_name
                    }
                    
                    # Save cache every 20 new entries to avoid disk I/O overhead
                    if len(IP_CACHE) % 20 == 0:
                        save_ip_cache(IP_CACHE)
                        
                    return country
                else:
                    logger.warning(f"API {endpoint_name} returned no country code for IP {ip_address}")
            except Exception as e:
                logger.warning(f"Error parsing response from {endpoint_name} for IP {ip_address}: {str(e)}")
                continue
        except Exception as e:
            logger.warning(f"Error querying {endpoint_name} for IP {ip_address}: {str(e)}")
            continue
    
    logger.error(f"Failed to determine location for IP {ip_address} after trying all APIs")
    return None


# Register exit handler to save cache when the program exits
import atexit
atexit.register(lambda: save_ip_cache(IP_CACHE))


async def is_valid_ip(ip: str) -> bool:
    """
    Check if a string is a valid IP address.

    This function uses the ipaddress module to try to create an IP address object from the string.

    Args:
        ip (str): The string to check.

    Returns:
        bool: True if the string is a valid IP address, False otherwise.
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
        return not ip_obj.is_private
    except ValueError:
        return False


IP_V6_REGEX = re.compile(r"\[([0-9a-fA-F:]+)\]:\d+\s+accepted")
IP_V4_REGEX = re.compile(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")
EMAIL_REGEX = re.compile(r"email:\s*([A-Za-z0-9._%+-]+)")


async def parse_logs(log: str) -> dict[str, UserType] | dict:  # pylint: disable=too-many-branches
    """
    Asynchronously parse logs to extract and validate IP addresses and emails.

    Args:
        log (str): The log to parse.

    Returns:
        list[UserType]
    """
    data = await read_config()
    if data.get("INVALID_IPS"):
        INVALID_IPS.update(data.get("INVALID_IPS"))
    lines = log.splitlines()
    
    ip_location_checked = 0
    ip_location_matches = 0
    ip_location_mismatches = 0
    
    for line in lines:
        if "accepted" not in line:
            continue
        if "BLOCK]" in line:
            continue
        ip_v6_match = IP_V6_REGEX.search(line)
        ip_v4_match = IP_V4_REGEX.search(line)
        email_match = EMAIL_REGEX.search(line)
        if ip_v6_match:
            ip = ip_v6_match.group(1)
        elif ip_v4_match:
            ip = ip_v4_match.group(1)
        else:
            continue
        if ip not in VALID_IPS:
            is_valid_ip_test = await is_valid_ip(ip)
            if is_valid_ip_test and ip not in INVALID_IPS:
                # Check if IP location check is enabled
                if data.get("ENABLE_IP_LOCATION_CHECK", True) and data["IP_LOCATION"] != "None":
                    ip_location_checked += 1
                    logger.debug(f"Checking location for IP: {ip}")
                    country = await check_ip(ip)
                    
                    if country and country == data["IP_LOCATION"]:
                        logger.debug(f"IP {ip} location {country} matches configured location {data['IP_LOCATION']}")
                        VALID_IPS.append(ip)
                        ip_location_matches += 1
                    elif country and country != data["IP_LOCATION"]:
                        logger.info(f"IP {ip} location {country} does not match configured location {data['IP_LOCATION']}")
                        INVALID_IPS.add(ip)
                        ip_location_mismatches += 1
                        continue
                    else:
                        logger.warning(f"Could not determine location for IP {ip}, treating as valid")
                        VALID_IPS.append(ip)
                else:
                    # If IP location check is disabled, accept all valid IPs
                    logger.debug(f"IP location check disabled, accepting valid IP: {ip}")
                    VALID_IPS.append(ip)
            else:
                if not is_valid_ip_test:
                    logger.debug(f"Invalid IP format: {ip}")
                else:
                    logger.debug(f"IP in blacklist: {ip}")
                continue
        if email_match:
            email = email_match.group(1)
            email = await remove_id_from_username(email)
            if email in INVALID_EMAILS:
                logger.debug(f"Invalid email format: {email}")
                continue
        else:
            continue

        user = ACTIVE_USERS.get(email)
        if user:
            user.ip.append(ip)
        else:
            user = ACTIVE_USERS.setdefault(
                email,
                UserType(name=email, ip=[ip]),
            )
            
        # Store in Redis
        try:
            # Make sure Redis client is initialized
            if not hasattr(redis_client, "_initialized") or not redis_client._initialized:
                await redis_client.initialize()
            
            # Add IP to Redis with the service name (user email)
            await redis_client.add_ip_to_service(email, ip)
        except Exception as e:
            # Don't interrupt the main flow if Redis fails
            logger.error(f"Error storing IP in Redis: {e}")
    
    # Log IP location checking statistics
    if ip_location_checked > 0:
        logger.info(f"IP location check summary: {ip_location_checked} checked, "
                   f"{ip_location_matches} matched, {ip_location_mismatches} mismatched")
    
    # Save IP cache to disk if we processed a significant number of IPs
    if ip_location_checked > 10:
        save_ip_cache(IP_CACHE)

    return ACTIVE_USERS
