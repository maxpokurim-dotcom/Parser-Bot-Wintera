"""
Timezone utilities - Moscow time (Europe/Moscow)
All operations in the system use Moscow timezone
"""
import logging
from datetime import datetime, timedelta, time
from typing import Optional, Tuple, List, Dict

logger = logging.getLogger(__name__)

# Try to import pytz, fallback to manual offset
try:
    import pytz
    MOSCOW_TZ = pytz.timezone('Europe/Moscow')
    HAS_PYTZ = True
except ImportError:
    MOSCOW_TZ = None
    HAS_PYTZ = False
    logger.warning("pytz not installed, using manual UTC+3 offset")


# ==================== CORE FUNCTIONS ====================

def now_moscow() -> datetime:
    """Get current time in Moscow timezone"""
    if HAS_PYTZ and MOSCOW_TZ:
        return datetime.now(MOSCOW_TZ)
    return datetime.utcnow() + timedelta(hours=3)


def today_moscow() -> datetime:
    """Get today's date at midnight in Moscow timezone"""
    now = now_moscow()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def to_moscow(dt: datetime) -> datetime:
    """Convert datetime to Moscow timezone"""
    if dt is None:
        return None
    
    if HAS_PYTZ and MOSCOW_TZ:
        if dt.tzinfo is None:
            # Assume UTC if no timezone
            import pytz
            dt = pytz.UTC.localize(dt)
        return dt.astimezone(MOSCOW_TZ)
    else:
        # Manual conversion assuming UTC
        if dt.tzinfo is None:
            return dt + timedelta(hours=3)
        return dt


def from_moscow_to_utc(dt: datetime) -> datetime:
    """Convert Moscow time to UTC"""
    if dt is None:
        return None
    
    if HAS_PYTZ and MOSCOW_TZ:
        if dt.tzinfo is None:
            dt = MOSCOW_TZ.localize(dt)
        import pytz
        return dt.astimezone(pytz.UTC)
    else:
        return dt - timedelta(hours=3)


# ==================== FORMATTING ====================

def format_moscow(dt: datetime, fmt: str = '%d.%m.%Y %H:%M') -> str:
    """Format datetime in Moscow timezone"""
    if dt is None:
        return '-'
    try:
        moscow_dt = to_moscow(dt)
        return moscow_dt.strftime(fmt)
    except Exception as e:
        logger.error(f"format_moscow error: {e}")
        return dt.strftime(fmt) if dt else '-'


def format_date(dt: datetime) -> str:
    """Format date only"""
    return format_moscow(dt, '%d.%m.%Y')


def format_time(dt: datetime) -> str:
    """Format time only"""
    return format_moscow(dt, '%H:%M')


def format_datetime(dt: datetime) -> str:
    """Format full datetime"""
    return format_moscow(dt, '%d.%m.%Y %H:%M:%S')


def format_relative(dt: datetime) -> str:
    """Format relative time (e.g., '5 минут назад')"""
    if dt is None:
        return '-'
    
    now = now_moscow()
    moscow_dt = to_moscow(dt)
    diff = now - moscow_dt
    
    if diff.total_seconds() < 0:
        # Future
        diff = -diff
        prefix = "через "
        suffix = ""
    else:
        prefix = ""
        suffix = " назад"
    
    seconds = int(diff.total_seconds())
    
    if seconds < 60:
        return f"{prefix}{seconds} сек{suffix}"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{prefix}{minutes} мин{suffix}"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{prefix}{hours} ч{suffix}"
    else:
        days = seconds // 86400
        return f"{prefix}{days} дн{suffix}"


# ==================== PARSING ====================

def parse_datetime(dt_string: str) -> Optional[datetime]:
    """Parse ISO datetime string to Moscow timezone"""
    if not dt_string:
        return None
    try:
        # Handle ISO format with Z
        dt_string = dt_string.replace('Z', '+00:00')
        dt = datetime.fromisoformat(dt_string)
        return to_moscow(dt)
    except Exception as e:
        logger.error(f"parse_datetime error: {e}")
        return None


def parse_time_input(text: str) -> Optional[datetime]:
    """
    Parse user time input to datetime
    Supports formats:
    - HH:MM (today or tomorrow)
    - DD.MM.YYYY HH:MM
    - YYYY-MM-DD HH:MM
    """
    import re
    text = text.strip()
    now = now_moscow()
    
    try:
        # Format: HH:MM
        if re.match(r'^\d{1,2}:\d{2}$', text):
            h, m = map(int, text.split(':'))
            if h > 23 or m > 59:
                return None
            result = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if result <= now:
                result += timedelta(days=1)
            return result
        
        # Format: DD.MM.YYYY HH:MM
        if re.match(r'^\d{1,2}\.\d{2}\.\d{4}\s+\d{1,2}:\d{2}$', text):
            dt = datetime.strptime(text, '%d.%m.%Y %H:%M')
            if HAS_PYTZ and MOSCOW_TZ:
                dt = MOSCOW_TZ.localize(dt)
            return dt
        
        # Format: YYYY-MM-DD HH:MM
        if re.match(r'^\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}$', text):
            dt = datetime.strptime(text, '%Y-%m-%d %H:%M')
            if HAS_PYTZ and MOSCOW_TZ:
                dt = MOSCOW_TZ.localize(dt)
            return dt
        
        # Format: DD.MM HH:MM (current year)
        if re.match(r'^\d{1,2}\.\d{2}\s+\d{1,2}:\d{2}$', text):
            dt = datetime.strptime(f"{text} {now.year}", '%d.%m %H:%M %Y')
            if HAS_PYTZ and MOSCOW_TZ:
                dt = MOSCOW_TZ.localize(dt)
            return dt
        
    except Exception as e:
        logger.error(f"parse_time_input error: {e}")
    
    return None


def parse_time_range(text: str) -> Optional[Tuple[time, time]]:
    """
    Parse time range (e.g., '09:00-18:00')
    Returns tuple of (start_time, end_time)
    """
    import re
    match = re.match(r'^(\d{1,2}):(\d{2})\s*[-–—]\s*(\d{1,2}):(\d{2})$', text.strip())
    if not match:
        return None
    
    sh, sm, eh, em = map(int, match.groups())
    if sh > 23 or sm > 59 or eh > 23 or em > 59:
        return None
    
    return (time(sh, sm), time(eh, em))


# ==================== BUSINESS LOGIC ====================

def is_quiet_hours(start: str, end: str) -> bool:
    """
    Check if current Moscow time is within quiet hours
    start/end format: "HH:MM"
    """
    if not start or not end:
        return False
    
    try:
        now = now_moscow()
        current = now.time()
        
        start_time = time(*map(int, start.split(':')))
        end_time = time(*map(int, end.split(':')))
        
        # Handle overnight range (e.g., 23:00 - 08:00)
        if start_time > end_time:
            return current >= start_time or current <= end_time
        else:
            return start_time <= current <= end_time
    except Exception as e:
        logger.error(f"is_quiet_hours error: {e}")
        return False


def get_next_active_time(start: str, end: str) -> datetime:
    """
    Get next datetime when quiet hours end
    Returns datetime in Moscow timezone
    """
    if not start or not end:
        return now_moscow()
    
    try:
        now = now_moscow()
        end_time = time(*map(int, end.split(':')))
        
        # Create datetime for today at end_time
        result = now.replace(hour=end_time.hour, minute=end_time.minute, second=0, microsecond=0)
        
        # If already passed today, move to tomorrow
        if result <= now:
            result += timedelta(days=1)
        
        return result
    except Exception as e:
        logger.error(f"get_next_active_time error: {e}")
        return now_moscow()


def is_working_hours(start_hour: int = 9, end_hour: int = 21) -> bool:
    """Check if current Moscow time is within working hours"""
    now = now_moscow()
    return start_hour <= now.hour < end_hour


def get_day_of_week() -> int:
    """Get current day of week in Moscow (0=Monday, 6=Sunday)"""
    return now_moscow().weekday()


def is_weekend() -> bool:
    """Check if today is weekend in Moscow"""
    return get_day_of_week() >= 5


DAY_NAMES_RU = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
DAY_NAMES_FULL = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']


def get_day_name(day: int, full: bool = False) -> str:
    """Get Russian day name by number (0=Monday)"""
    names = DAY_NAMES_FULL if full else DAY_NAMES_RU
    return names[day % 7]


# ==================== SCHEDULING ====================

def get_optimal_time_slots(heatmap: Dict, count: int = 5) -> List[Dict]:
    """
    Get optimal time slots from heatmap data
    heatmap format: {day: {hour: score}}
    Returns list of {day, hour, score, day_name, formatted}
    """
    slots = []
    
    for day, hours in heatmap.items():
        for hour, score in hours.items():
            slots.append({
                'day': int(day),
                'hour': int(hour),
                'score': float(score),
                'day_name': DAY_NAMES_RU[int(day) % 7],
                'formatted': f"{DAY_NAMES_RU[int(day) % 7]} {int(hour):02d}:00"
            })
    
    # Sort by score descending
    slots.sort(key=lambda x: x['score'], reverse=True)
    
    return slots[:count]


def get_next_slot_datetime(day: int, hour: int) -> datetime:
    """
    Get next occurrence of specific day and hour
    day: 0=Monday, hour: 0-23
    Returns datetime in Moscow timezone
    """
    now = now_moscow()
    current_day = now.weekday()
    
    # Days until target day
    days_ahead = day - current_day
    if days_ahead < 0:
        days_ahead += 7
    elif days_ahead == 0 and now.hour >= hour:
        days_ahead = 7
    
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    target += timedelta(days=days_ahead)
    
    return target


# ==================== SEASONAL ADJUSTMENTS ====================

def get_seasonal_context() -> Dict:
    """
    Get seasonal context for behavior adjustments
    Returns dict with seasonal info and adjustments
    """
    now = now_moscow()
    month = now.month
    day = now.day
    
    context = {
        'season': 'normal',
        'holiday': None,
        'activity_multiplier': 1.0,
        'tone': 'professional',
        'emoji_boost': []
    }
    
    # New Year period (Dec 25 - Jan 10)
    if (month == 12 and day >= 25) or (month == 1 and day <= 10):
        context.update({
            'season': 'new_year',
            'holiday': 'Новый Год',
            'activity_multiplier': 0.5,
            'tone': 'celebratory',
            'emoji_boost': ['🎄', '🎁', '❄️', '🎉']
        })
    
    # May holidays (May 1-10)
    elif month == 5 and day <= 10:
        context.update({
            'season': 'may_holidays',
            'holiday': 'Майские праздники',
            'activity_multiplier': 0.6,
            'tone': 'relaxed',
            'emoji_boost': ['🌸', '☀️', '🎉']
        })
    
    # Summer (June-August)
    elif month in [6, 7, 8]:
        context.update({
            'season': 'summer',
            'activity_multiplier': 0.8,
            'tone': 'relaxed',
            'emoji_boost': ['☀️', '🏖️']
        })
    
    # Weekend adjustment
    if is_weekend():
        context['activity_multiplier'] *= 0.7
        if context['tone'] == 'professional':
            context['tone'] = 'relaxed'
    
    return context


def should_reduce_activity() -> bool:
    """Check if activity should be reduced based on time/season"""
    context = get_seasonal_context()
    
    # Reduce if multiplier is significantly lower
    if context['activity_multiplier'] < 0.7:
        return True
    
    # Reduce during night hours (00:00 - 07:00)
    hour = now_moscow().hour
    if 0 <= hour < 7:
        return True
    
    return False
