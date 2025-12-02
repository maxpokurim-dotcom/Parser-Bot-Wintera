"""
Helper utilities
"""
import re
import random
import hashlib
from typing import Optional, Tuple
from urllib.parse import urlparse


def mask_phone(phone: str) -> str:
    """Mask phone number for logging"""
    if len(phone) > 6:
        return f"{phone[:4]}***{phone[-2:]}"
    return phone


def generate_random_delay(min_delay: int, max_delay: int) -> float:
    """Generate random delay with some variance"""
    base_delay = random.uniform(min_delay, max_delay)
    # Add small random variance (+/- 10%)
    variance = base_delay * 0.1
    return base_delay + random.uniform(-variance, variance)


def safe_filename(text: str, max_length: int = 50) -> str:
    """Convert text to safe filename"""
    # Remove unsafe characters
    safe = re.sub(r'[^\w\s\-_]', '', text)
    # Replace spaces with underscores
    safe = safe.replace(' ', '_')
    # Limit length
    if len(safe) > max_length:
        safe = safe[:max_length]
    return safe.lower()


def parse_proxy(proxy_string: Optional[str]) -> Optional[dict]:
    """
    Parse proxy string into components
    
    Supports formats:
    - socks5://user:pass@host:port
    - http://user:pass@host:port
    - host:port
    - user:pass@host:port
    
    Returns:
        dict with proxy_type, addr, port, username, password
        or None if invalid
    """
    if not proxy_string:
        return None
    
    try:
        # Parse URL-like format
        if '://' in proxy_string:
            parsed = urlparse(proxy_string)
            return {
                'proxy_type': parsed.scheme.lower(),  # socks5, socks4, http
                'addr': parsed.hostname,
                'port': parsed.port,
                'username': parsed.username,
                'password': parsed.password,
            }
        
        # Parse simple formats
        if '@' in proxy_string:
            auth, host_port = proxy_string.rsplit('@', 1)
            username, password = auth.split(':', 1)
        else:
            host_port = proxy_string
            username = None
            password = None
        
        host, port = host_port.split(':')
        
        return {
            'proxy_type': 'socks5',  # default
            'addr': host,
            'port': int(port),
            'username': username,
            'password': password,
        }
    except Exception:
        return None


def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable string"""
    if seconds < 60:
        return f"{seconds} сек"
    elif seconds < 3600:
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes} мин {secs} сек"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours} ч {minutes} мин"


def generate_session_name(phone: str, user_id: int) -> str:
    """Generate unique session name from phone and user_id"""
    # Create hash to avoid exposing phone in filenames
    data = f"{phone}:{user_id}"
    hash_str = hashlib.md5(data.encode()).hexdigest()[:12]
    return f"session_{hash_str}"


def extract_username(text: str) -> Optional[str]:
    """Extract username from text (with or without @)"""
    if not text:
        return None
    
    text = text.strip()
    
    # Handle t.me/username links
    if 't.me/' in text:
        parts = text.split('t.me/')[-1].split('/')
        return parts[0].replace('@', '')
    
    # Handle @username
    if text.startswith('@'):
        return text[1:]
    
    # Just username
    if re.match(r'^[a-zA-Z][a-zA-Z0-9_]{4,31}$', text):
        return text
    
    return None


def chunk_list(lst: list, chunk_size: int) -> list:
    """Split list into chunks"""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def calculate_reliability_score(
    successful_sends: int,
    failed_sends: int,
    consecutive_errors: int,
    flood_waits: int,
    age_days: int
) -> float:
    """
    Calculate account reliability score (0-100)
    
    Factors:
    - Success rate: 40%
    - Consecutive errors: 25%
    - Flood waits: 20%
    - Account age: 15%
    """
    total_sends = successful_sends + failed_sends
    
    # Success rate (40 points max)
    if total_sends > 0:
        success_rate = (successful_sends / total_sends) * 40
    else:
        success_rate = 40  # New accounts start with full score
    
    # Consecutive errors penalty (25 points max)
    errors_penalty = min(consecutive_errors * 5, 25)
    errors_score = 25 - errors_penalty
    
    # Flood waits penalty (20 points max)
    flood_penalty = min(flood_waits * 4, 20)
    flood_score = 20 - flood_penalty
    
    # Account age bonus (15 points max)
    if age_days >= 365:
        age_score = 15
    elif age_days >= 90:
        age_score = 12
    elif age_days >= 30:
        age_score = 8
    elif age_days >= 7:
        age_score = 5
    else:
        age_score = 2
    
    return max(0, min(100, success_rate + errors_score + flood_score + age_score))
