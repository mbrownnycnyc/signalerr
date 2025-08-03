
import logging
import re
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def format_phone_number(phone: str) -> str:
    """Format phone number to international format"""
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone)
    
    # Add + prefix if not present
    if not phone.startswith('+'):
        if len(digits) == 10:  # US number without country code
            return f"+1{digits}"
        elif len(digits) == 11 and digits.startswith('1'):  # US number with country code
            return f"+{digits}"
        else:
            return f"+{digits}"
    
    return phone

def validate_phone_number(phone: str) -> bool:
    """Validate phone number format"""
    # Should start with + and have 10-15 digits
    pattern = r'^\+\d{10,15}$'
    return bool(re.match(pattern, phone))

def parse_seasons_from_text(text: str) -> Optional[List[int]]:
    """Parse season numbers from text"""
    # Look for patterns like "season 1", "seasons 1-3", "s1-s3", etc.
    patterns = [
        r'seasons?\s*(\d+)(?:\s*[-–]\s*(\d+))?',
        r's(\d+)(?:\s*[-–]\s*s?(\d+))?',
        r'season\s*(\d+)(?:\s*to\s*(\d+))?',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) else start
            return list(range(start, end + 1))
    
    return None

def format_duration(seconds: int) -> str:
    """Format duration in seconds to human readable format"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if minutes > 0:
            return f"{hours}h {minutes}m"
        return f"{hours}h"

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to maximum length"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe storage"""
    # Remove or replace unsafe characters
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip(' .')
    
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    
    return filename

def parse_media_year(date_string: str) -> Optional[int]:
    """Parse year from date string"""
    if not date_string:
        return None
    
    try:
        # Try to parse as ISO date
        date_obj = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        return date_obj.year
    except:
        # Try to extract year with regex
        year_match = re.search(r'(\d{4})', date_string)
        if year_match:
            year = int(year_match.group(1))
            # Validate year is reasonable
            current_year = datetime.now().year
            if 1900 <= year <= current_year + 5:
                return year
    
    return None

def format_file_size(size_bytes: int) -> str:
    """Format file size in bytes to human readable format"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"

def is_recent(timestamp: datetime, hours: int = 24) -> bool:
    """Check if timestamp is within recent hours"""
    if not timestamp:
        return False
    
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    return timestamp > cutoff

def extract_tmdb_id(url_or_id: str) -> Optional[int]:
    """Extract TMDB ID from URL or return ID if already numeric"""
    if not url_or_id:
        return None
    
    # If it's already a number
    if url_or_id.isdigit():
        return int(url_or_id)
    
    # Try to extract from TMDB URL
    tmdb_pattern = r'themoviedb\.org/(?:movie|tv)/(\d+)'
    match = re.search(tmdb_pattern, url_or_id)
    if match:
        return int(match.group(1))
    
    return None

def clean_search_query(query: str) -> str:
    """Clean and normalize search query"""
    # Remove extra whitespace
    query = ' '.join(query.split())
    
    # Remove common words that might interfere with search
    stop_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
    words = query.lower().split()
    
    # Only remove stop words if query has more than 2 words
    if len(words) > 2:
        words = [word for word in words if word not in stop_words]
        query = ' '.join(words)
    
    return query.strip()

def generate_request_summary(request_data: Dict[str, Any]) -> str:
    """Generate a summary string for a request"""
    title = request_data.get('title', 'Unknown')
    year = request_data.get('year')
    media_type = request_data.get('media_type', 'unknown')
    seasons = request_data.get('seasons_requested', [])
    
    summary = title
    if year:
        summary += f" ({year})"
    
    if media_type == 'tv' and seasons:
        if len(seasons) == 1:
            summary += f" - Season {seasons[0]}"
        else:
            summary += f" - Seasons {seasons[0]}-{seasons[-1]}"
    
    return summary

def validate_settings_value(key: str, value: str) -> tuple:
    """Validate settings value based on key"""
    try:
        if key in ['request_timeout_minutes', 'max_requests_per_user_per_day']:
            val = int(value)
            if val < 1 or val > 1440:  # 1 minute to 24 hours
                return False, "Value must be between 1 and 1440"
        
        elif key == 'default_verbosity':
            if value not in ['casual', 'simple', 'verbose']:
                return False, "Must be one of: casual, simple, verbose"
        
        elif key in ['bot_enabled', 'enable_group_chats', 'enable_auto_notifications', 'maintenance_mode']:
            if value.lower() not in ['true', 'false']:
                return False, "Must be true or false"
        
        elif key == 'overseerr_url':
            if not value.startswith(('http://', 'https://')):
                return False, "Must be a valid HTTP/HTTPS URL"
        
        elif key == 'admin_phone_numbers':
            phones = [phone.strip() for phone in value.split(',') if phone.strip()]
            for phone in phones:
                if not validate_phone_number(phone):
                    return False, f"Invalid phone number format: {phone}"
        
        return True, ""
    
    except ValueError as e:
        return False, str(e)

class RateLimiter:
    """Simple rate limiter for user actions"""
    
    def __init__(self):
        self.user_actions = {}
    
    def is_allowed(self, user_id: str, action: str, limit: int, window_seconds: int = 3600) -> bool:
        """Check if user action is allowed within rate limit"""
        now = datetime.utcnow()
        key = f"{user_id}:{action}"
        
        if key not in self.user_actions:
            self.user_actions[key] = []
        
        # Clean old entries
        cutoff = now - timedelta(seconds=window_seconds)
        self.user_actions[key] = [
            timestamp for timestamp in self.user_actions[key] 
            if timestamp > cutoff
        ]
        
        # Check if under limit
        if len(self.user_actions[key]) >= limit:
            return False
        
        # Add current action
        self.user_actions[key].append(now)
        return True
    
    def get_remaining(self, user_id: str, action: str, limit: int, window_seconds: int = 3600) -> int:
        """Get remaining actions for user"""
        now = datetime.utcnow()
        key = f"{user_id}:{action}"
        
        if key not in self.user_actions:
            return limit
        
        # Clean old entries
        cutoff = now - timedelta(seconds=window_seconds)
        self.user_actions[key] = [
            timestamp for timestamp in self.user_actions[key] 
            if timestamp > cutoff
        ]
        
        return max(0, limit - len(self.user_actions[key]))
