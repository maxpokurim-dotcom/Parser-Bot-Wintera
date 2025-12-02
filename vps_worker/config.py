"""
VPS Worker Configuration
Loads settings from environment variables
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import Optional, List

# Load .env file
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.absolute()
SESSIONS_DIR = Path(os.getenv('SESSIONS_DIR', BASE_DIR / 'sessions'))
LOGS_DIR = Path(os.getenv('LOGS_DIR', BASE_DIR / 'logs'))
DATA_DIR = Path(os.getenv('DATA_DIR', BASE_DIR / 'data'))

# Create directories
SESSIONS_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)


@dataclass
class SupabaseConfig:
    """Supabase database configuration"""
    url: str = field(default_factory=lambda: os.getenv('SUPABASE_URL', ''))
    key: str = field(default_factory=lambda: os.getenv('SUPABASE_KEY', ''))
    service_key: str = field(default_factory=lambda: os.getenv('SUPABASE_SERVICE_KEY', ''))
    
    def __post_init__(self):
        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY are required")


@dataclass
class TelegramConfig:
    """Telegram API configuration"""
    api_id: int = field(default_factory=lambda: int(os.getenv('TELEGRAM_API_ID', 0)))
    api_hash: str = field(default_factory=lambda: os.getenv('TELEGRAM_API_HASH', ''))
    bot_token: str = field(default_factory=lambda: os.getenv('BOT_TOKEN', ''))
    admin_chat_id: int = field(default_factory=lambda: int(os.getenv('ADMIN_CHAT_ID', 0)))
    
    def __post_init__(self):
        if not self.api_id or not self.api_hash:
            raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH are required")


@dataclass
class MailingConfig:
    """Mailing settings"""
    delay_min: int = field(default_factory=lambda: int(os.getenv('MAILING_DELAY_MIN', 30)))
    delay_max: int = field(default_factory=lambda: int(os.getenv('MAILING_DELAY_MAX', 90)))
    warm_start_count: int = field(default_factory=lambda: int(os.getenv('WARM_START_COUNT', 10)))
    warm_start_multiplier: float = field(default_factory=lambda: float(os.getenv('WARM_START_MULTIPLIER', 2.0)))
    typing_delay_min: int = field(default_factory=lambda: int(os.getenv('TYPING_DELAY_MIN', 2)))
    typing_delay_max: int = field(default_factory=lambda: int(os.getenv('TYPING_DELAY_MAX', 8)))


@dataclass
class ParsingConfig:
    """Parsing settings"""
    batch_size: int = field(default_factory=lambda: int(os.getenv('PARSING_BATCH_SIZE', 100)))
    delay: int = field(default_factory=lambda: int(os.getenv('PARSING_DELAY', 5)))


@dataclass
class HerderConfig:
    """Herder (bot activity) settings"""
    delay_min: int = field(default_factory=lambda: int(os.getenv('HERDER_DELAY_MIN', 300)))
    delay_max: int = field(default_factory=lambda: int(os.getenv('HERDER_DELAY_MAX', 3600)))
    max_daily_actions: int = field(default_factory=lambda: int(os.getenv('HERDER_MAX_DAILY_ACTIONS', 50)))


@dataclass
class WarmupConfig:
    """Account warmup settings"""
    actions_per_day: int = field(default_factory=lambda: int(os.getenv('WARMUP_ACTIONS_PER_DAY', 10)))
    channels: List[str] = field(default_factory=lambda: os.getenv('WARMUP_CHANNELS', 'telegram,durov').split(','))


@dataclass
class WorkerConfig:
    """Worker process settings"""
    poll_interval: int = field(default_factory=lambda: int(os.getenv('POLL_INTERVAL', 10)))
    max_concurrent_tasks: int = field(default_factory=lambda: int(os.getenv('MAX_CONCURRENT_TASKS', 5)))
    max_consecutive_errors: int = field(default_factory=lambda: int(os.getenv('MAX_CONSECUTIVE_ERRORS', 5)))
    flood_protection: bool = field(default_factory=lambda: os.getenv('FLOOD_PROTECTION', 'true').lower() == 'true')


@dataclass
class Config:
    """Main configuration container"""
    supabase: SupabaseConfig = field(default_factory=SupabaseConfig)
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    mailing: MailingConfig = field(default_factory=MailingConfig)
    parsing: ParsingConfig = field(default_factory=ParsingConfig)
    herder: HerderConfig = field(default_factory=HerderConfig)
    warmup: WarmupConfig = field(default_factory=WarmupConfig)
    worker: WorkerConfig = field(default_factory=WorkerConfig)
    
    # API keys
    onlinesim_api_key: str = field(default_factory=lambda: os.getenv('ONLINESIM_API_KEY', ''))
    openai_api_key: str = field(default_factory=lambda: os.getenv('OPENAI_API_KEY', ''))
    
    # Proxy
    default_proxy: Optional[str] = field(default_factory=lambda: os.getenv('DEFAULT_PROXY') or None)
    
    # Security
    encryption_key: Optional[str] = field(default_factory=lambda: os.getenv('ENCRYPTION_KEY') or None)


def get_config() -> Config:
    """Get configuration singleton"""
    return Config()


# Global config instance
config = get_config()
