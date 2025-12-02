"""
Logging configuration
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import structlog

# Color support
try:
    from colorama import init, Fore, Style
    init()
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False


def setup_logger(
    name: str = 'vps_worker',
    log_dir: Optional[Path] = None,
    level: int = logging.INFO,
    console: bool = True
) -> logging.Logger:
    """
    Setup logger with file and console handlers
    
    Args:
        name: Logger name
        log_dir: Directory for log files
        level: Logging level
        console: Enable console output
    
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        
        if COLORS_AVAILABLE:
            console_formatter = ColoredFormatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
        else:
            console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
    
    # File handler
    if log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Main log file
        log_file = log_dir / f'{name}.log'
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Error log file
        error_file = log_dir / f'{name}_errors.log'
        error_handler = logging.FileHandler(error_file, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
    
    return logger


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""
    
    COLORS = {
        'DEBUG': Fore.CYAN if COLORS_AVAILABLE else '',
        'INFO': Fore.GREEN if COLORS_AVAILABLE else '',
        'WARNING': Fore.YELLOW if COLORS_AVAILABLE else '',
        'ERROR': Fore.RED if COLORS_AVAILABLE else '',
        'CRITICAL': Fore.RED + Style.BRIGHT if COLORS_AVAILABLE else '',
    }
    RESET = Style.RESET_ALL if COLORS_AVAILABLE else ''
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        record.levelname = f'{color}{record.levelname}{self.RESET}'
        return super().format(record)


def get_logger(name: str) -> logging.Logger:
    """Get a child logger"""
    return logging.getLogger(f'vps_worker.{name}')


# Configure structlog for async logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
