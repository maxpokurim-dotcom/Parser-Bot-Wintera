"""
Timezone utilities - Moscow Time (Europe/Moscow)
All bot operations use Moscow timezone
"""
from datetime import datetime, timedelta
from typing import Optional

try:
    import pytz
    MOSCOW_TZ = pytz.timezone('Europe/Moscow')
    UTC_TZ = pytz.UTC
    HAS_PYTZ = True
except ImportError:
    MOSCOW_TZ = None
    UTC_TZ = None
    HAS_PYTZ = False


def now_moscow() -> datetime:
    """Get current time in Moscow timezone"""
    if HAS_PYTZ:
        return datetime.now(MOSCOW_TZ)
    # Fallback: UTC + 3 hours
    return datetime.utcnow() + timedelta(hours=3)


def now_utc() -> datetime:
    """Get current UTC time"""
    if HAS_PYTZ:
        return datetime.now(UTC_TZ)
    return datetime.utcnow()


def to_moscow(dt: datetime) -> datetime:
    """Convert datetime to Moscow timezone"""
    if dt is None:
        return None
    
    if HAS_PYTZ:
        if dt.tzinfo is None:
            # Assume UTC if no timezone
            dt = UTC_TZ.localize(dt)
        return dt.astimezone(MOSCOW_TZ)
    
    # Fallback: assume UTC, add 3 hours
    if dt.tzinfo is None:
        return dt + timedelta(hours=3)
    return dt


def to_utc(dt: datetime) -> datetime:
    """Convert datetime to UTC"""
    if dt is None:
        return None
    
    if HAS_PYTZ:
        if dt.tzinfo is None:
            # Assume Moscow if no timezone
            dt = MOSCOW_TZ.localize(dt)
        return dt.astimezone(UTC_TZ)
    
    # Fallback: assume Moscow, subtract 3 hours
    if dt.tzinfo is None:
        return dt - timedelta(hours=3)
    return dt


def format_moscow(dt: datetime, fmt: str = '%d.%m.%Y %H:%M') -> str:
    """Format datetime in Moscow timezone"""
    if dt is None:
        return '-'
    try:
        moscow_dt = to_moscow(dt)
        return moscow_dt.strftime(fmt)
    except Exception:
        try:
            return dt.strftime(fmt)
        except:
            return '-'


def format_date(dt: datetime) -> str:
    """Format date only"""
    return format_moscow(dt, '%d.%m.%Y')


def format_time(dt: datetime) -> str:
    """Format time only"""
    return format_moscow(dt, '%H:%M')


def format_datetime_short(dt: datetime) -> str:
    """Format datetime short"""
    return format_moscow(dt, '%d.%m %H:%M')


def format_datetime_full(dt: datetime) -> str:
    """Format datetime with seconds"""
    return format_moscow(dt, '%d.%m.%Y %H:%M:%S')


def parse_datetime(dt_string: str) -> Optional[datetime]:
    """Parse ISO datetime string to Moscow timezone"""
    if not dt_string:
        return None
    
    try:
        # Handle various formats
        dt_string = dt_string.replace('Z', '+00:00')
        
        # Try parsing with timezone
        if '+' in dt_string or '-' in dt_string[10:]:  # Has timezone
            dt = datetime.fromisoformat(dt_string)
        else:
            # No timezone - assume UTC
            dt = datetime.fromisoformat(dt_string)
            if HAS_PYTZ:
                dt = UTC_TZ.localize(dt)
        
        return to_moscow(dt)
    except Exception:
        return None


def parse_date(date_string: str) -> Optional[datetime]:
    """Parse date string (YYYY-MM-DD or DD.MM.YYYY)"""
    if not date_string:
        return None
    
    try:
        # Try ISO format first
        if '-' in date_string and len(date_string) == 10:
            dt = datetime.strptime(date_string, '%Y-%m-%d')
        # Try Russian format
        elif '.' in date_string:
            dt = datetime.strptime(date_string, '%d.%m.%Y')
        else:
            return None
        
        if HAS_PYTZ:
            dt = MOSCOW_TZ.localize(dt)
        
        return dt
    except Exception:
        return None


def parse_time(time_string: str) -> Optional[tuple]:
    """Parse time string (HH:MM) to tuple (hour, minute)"""
    if not time_string:
        return None
    
    try:
        parts = time_string.split(':')
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return (hour, minute)
        return None
    except Exception:
        return None


def get_today_start_moscow() -> datetime:
    """Get start of today (00:00) in Moscow timezone"""
    now = now_moscow()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def get_today_end_moscow() -> datetime:
    """Get end of today (23:59:59) in Moscow timezone"""
    now = now_moscow()
    return now.replace(hour=23, minute=59, second=59, microsecond=999999)


def get_week_start_moscow() -> datetime:
    """Get start of current week (Monday 00:00) in Moscow timezone"""
    now = now_moscow()
    days_since_monday = now.weekday()
    monday = now - timedelta(days=days_since_monday)
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)


def get_month_start_moscow() -> datetime:
    """Get start of current month in Moscow timezone"""
    now = now_moscow()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def is_quiet_hours(start_hour: int, end_hour: int) -> bool:
    """Check if current Moscow time is within quiet hours"""
    if start_hour is None or end_hour is None:
        return False
    
    current_hour = now_moscow().hour
    
    if start_hour <= end_hour:
        # Same day range (e.g., 01:00 - 07:00)
        return start_hour <= current_hour < end_hour
    else:
        # Overnight range (e.g., 23:00 - 07:00)
        return current_hour >= start_hour or current_hour < end_hour


def is_working_hours(start_hour: int = 10, end_hour: int = 22) -> bool:
    """Check if current Moscow time is within working hours"""
    current_hour = now_moscow().hour
    return start_hour <= current_hour < end_hour


def get_next_working_hour(start_hour: int = 10) -> datetime:
    """Get next working hour start time"""
    now = now_moscow()
    
    if now.hour >= start_hour:
        # Next day
        next_day = now + timedelta(days=1)
        return next_day.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    else:
        # Today
        return now.replace(hour=start_hour, minute=0, second=0, microsecond=0)


def seconds_until(target_hour: int, target_minute: int = 0) -> int:
    """Calculate seconds until specific time today or tomorrow"""
    now = now_moscow()
    target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    
    if target <= now:
        target += timedelta(days=1)
    
    return int((target - now).total_seconds())


def get_day_name(day_index: int) -> str:
    """Get Russian day name by index (0=Monday, 6=Sunday)"""
    days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье']
    return days[day_index] if 0 <= day_index <= 6 else ''


def get_day_name_short(day_index: int) -> str:
    """Get short Russian day name by index (0=Monday)"""
    days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    return days[day_index] if 0 <= day_index <= 6 else ''


def get_month_name(month: int) -> str:
    """Get Russian month name"""
    months = [
        '', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
    ]
    return months[month] if 1 <= month <= 12 else ''


def get_month_name_genitive(month: int) -> str:
    """Get Russian month name in genitive case"""
    months = [
        '', 'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
        'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
    ]
    return months[month] if 1 <= month <= 12 else ''


def format_relative_time(dt: datetime) -> str:
    """Format datetime as relative time (e.g., '5 минут назад')"""
    if dt is None:
        return '-'
    
    now = now_moscow()
    moscow_dt = to_moscow(dt)
    diff = now - moscow_dt
    
    seconds = int(diff.total_seconds())
    
    if seconds < 0:
        # Future
        seconds = abs(seconds)
        if seconds < 60:
            return 'через несколько секунд'
        elif seconds < 3600:
            minutes = seconds // 60
            return f'через {minutes} мин'
        elif seconds < 86400:
            hours = seconds // 3600
            return f'через {hours} ч'
        else:
            days = seconds // 86400
            return f'через {days} дн'
    
    # Past
    if seconds < 60:
        return 'только что'
    elif seconds < 3600:
        minutes = seconds // 60
        return f'{minutes} мин назад'
    elif seconds < 86400:
        hours = seconds // 3600
        return f'{hours} ч назад'
    elif seconds < 604800:
        days = seconds // 86400
        return f'{days} дн назад'
    else:
        return format_moscow(moscow_dt, '%d.%m.%Y')


def is_today(dt: datetime) -> bool:
    """Check if datetime is today (Moscow time)"""
    if dt is None:
        return False
    
    moscow_dt = to_moscow(dt)
    today = now_moscow()
    
    return moscow_dt.date() == today.date()


def is_yesterday(dt: datetime) -> bool:
    """Check if datetime is yesterday (Moscow time)"""
    if dt is None:
        return False
    
    moscow_dt = to_moscow(dt)
    yesterday = now_moscow() - timedelta(days=1)
    
    return moscow_dt.date() == yesterday.date()


def is_this_week(dt: datetime) -> bool:
    """Check if datetime is within current week (Moscow time)"""
    if dt is None:
        return False
    
    moscow_dt = to_moscow(dt)
    week_start = get_week_start_moscow()
    
    return moscow_dt >= week_start


def days_between(dt1: datetime, dt2: datetime) -> int:
    """Calculate days between two datetimes"""
    if dt1 is None or dt2 is None:
        return 0
    
    d1 = to_moscow(dt1).date()
    d2 = to_moscow(dt2).date()
    
    return abs((d2 - d1).days)


def add_days(dt: datetime, days: int) -> datetime:
    """Add days to datetime"""
    if dt is None:
        return None
    return dt + timedelta(days=days)


def add_hours(dt: datetime, hours: int) -> datetime:
    """Add hours to datetime"""
    if dt is None:
        return None
    return dt + timedelta(hours=hours)


def add_minutes(dt: datetime, minutes: int) -> datetime:
    """Add minutes to datetime"""
    if dt is None:
        return None
    return dt + timedelta(minutes=minutes)
