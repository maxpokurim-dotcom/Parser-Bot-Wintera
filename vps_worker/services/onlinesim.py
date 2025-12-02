"""
OnlineSim Service - SMS service for account creation
API documentation: https://onlinesim.io/openapi
"""
import os
import asyncio
import aiohttp
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta

from utils.logger import get_logger

logger = get_logger('onlinesim')


class OnlineSimError(Exception):
    """OnlineSim API error"""
    pass


class NumberStatus(Enum):
    """SMS number status"""
    PENDING = "pending"           # Waiting for SMS
    RECEIVED = "received"         # SMS received
    CANCELLED = "cancelled"       # Order cancelled
    TIMEOUT = "timeout"           # Timeout waiting for SMS
    USED = "used"                 # Number already used


@dataclass
class PhoneNumber:
    """Phone number from OnlineSim"""
    tzid: int                     # Transaction ID
    number: str                   # Phone number
    country: str                  # Country code
    service: str                  # Service (telegram)
    status: NumberStatus
    code: Optional[str] = None    # Received SMS code
    created_at: datetime = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.utcnow()


class OnlineSimService:
    """
    OnlineSim API client for receiving SMS codes
    Used for automatic account creation
    """
    
    BASE_URL = "https://onlinesim.io/api"
    
    # Country codes
    COUNTRIES = {
        'ru': 7,      # Russia
        'ua': 380,    # Ukraine  
        'kz': 77,     # Kazakhstan
        'by': 375,    # Belarus
        'pl': 48,     # Poland
        'de': 49,     # Germany
        'gb': 44,     # UK
        'us': 1,      # USA
        'tr': 90,     # Turkey
        'in': 91,     # India
    }
    
    # Service codes
    SERVICES = {
        'telegram': 'Telegram'
    }
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('ONLINESIM_API_KEY', '')
        self.default_country = os.getenv('ONLINESIM_DEFAULT_COUNTRY', 'ru')
        self.active_numbers: Dict[int, PhoneNumber] = {}  # tzid -> PhoneNumber
    
    async def _request(
        self, 
        endpoint: str, 
        params: Optional[Dict] = None,
        method: str = "GET"
    ) -> Dict:
        """Make API request"""
        if not self.api_key:
            raise OnlineSimError("OnlineSim API key not configured")
        
        params = params or {}
        params['apikey'] = self.api_key
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(url, params=params) as response:
                        data = await response.json()
                else:
                    async with session.post(url, data=params) as response:
                        data = await response.json()
                
                # Check for errors
                if data.get('response') == 'ERROR' or 'error' in data:
                    error_msg = data.get('error_msg') or data.get('error') or 'Unknown error'
                    raise OnlineSimError(f"OnlineSim API error: {error_msg}")
                
                return data
                
        except aiohttp.ClientError as e:
            raise OnlineSimError(f"OnlineSim request failed: {e}")
    
    async def get_balance(self) -> float:
        """Get account balance"""
        data = await self._request("getBalance.php")
        return float(data.get('balance', 0))
    
    async def get_prices(self, country: str = 'ru') -> Dict[str, float]:
        """Get prices for services"""
        country_code = self.COUNTRIES.get(country, 7)
        data = await self._request("getPrice.php", {'country': country_code})
        
        prices = {}
        if 'services' in data:
            for service, info in data['services'].items():
                prices[service] = float(info.get('price', 0))
        
        return prices
    
    async def get_number(
        self, 
        service: str = 'telegram',
        country: Optional[str] = None
    ) -> PhoneNumber:
        """
        Get new phone number for SMS
        
        Args:
            service: Service name (telegram)
            country: Country code (ru, ua, kz, etc.)
        
        Returns:
            PhoneNumber object
        """
        country = country or self.default_country
        country_code = self.COUNTRIES.get(country, 7)
        
        params = {
            'service': service,
            'country': country_code
        }
        
        data = await self._request("getNum.php", params)
        
        if 'tzid' not in data:
            raise OnlineSimError("Failed to get number: no tzid in response")
        
        # Extract number from response
        number = data.get('number', '')
        if not number.startswith('+'):
            number = '+' + number
        
        phone = PhoneNumber(
            tzid=int(data['tzid']),
            number=number,
            country=country,
            service=service,
            status=NumberStatus.PENDING
        )
        
        self.active_numbers[phone.tzid] = phone
        logger.info(f"Got number {phone.number} (tzid: {phone.tzid})")
        
        return phone
    
    async def get_state(self, tzid: int) -> Dict:
        """
        Get current state of number order
        
        Returns dict with:
        - response: status string
        - msg: SMS code if received
        """
        data = await self._request("getState.php", {'tzid': tzid})
        return data
    
    async def wait_for_code(
        self, 
        tzid: int, 
        timeout: int = 300,
        poll_interval: int = 5
    ) -> Optional[str]:
        """
        Wait for SMS code
        
        Args:
            tzid: Transaction ID
            timeout: Max wait time in seconds
            poll_interval: Check interval in seconds
        
        Returns:
            SMS code or None if timeout
        """
        start_time = datetime.utcnow()
        end_time = start_time + timedelta(seconds=timeout)
        
        logger.info(f"Waiting for SMS code (tzid: {tzid}, timeout: {timeout}s)")
        
        while datetime.utcnow() < end_time:
            try:
                state = await self.get_state(tzid)
                response = state.get('response')
                
                if response == 'TZ_NUM_ANSWER':
                    # Code received
                    code = state.get('msg', '')
                    # Extract digits from code (Telegram sends "Code: 12345")
                    import re
                    digits = re.findall(r'\d+', code)
                    if digits:
                        code = digits[-1]  # Last number is usually the code
                    
                    if tzid in self.active_numbers:
                        self.active_numbers[tzid].status = NumberStatus.RECEIVED
                        self.active_numbers[tzid].code = code
                    
                    logger.info(f"Received SMS code for tzid {tzid}")
                    return code
                
                elif response == 'TZ_OVER_EMPTY':
                    # Number cancelled or expired
                    if tzid in self.active_numbers:
                        self.active_numbers[tzid].status = NumberStatus.CANCELLED
                    raise OnlineSimError("Number order cancelled or expired")
                
                elif response == 'TZ_OVER_OK':
                    # Already used
                    if tzid in self.active_numbers:
                        self.active_numbers[tzid].status = NumberStatus.USED
                    raise OnlineSimError("Number already used")
                
                # Still waiting
                await asyncio.sleep(poll_interval)
                
            except OnlineSimError:
                raise
            except Exception as e:
                logger.error(f"Error checking SMS state: {e}")
                await asyncio.sleep(poll_interval)
        
        # Timeout
        if tzid in self.active_numbers:
            self.active_numbers[tzid].status = NumberStatus.TIMEOUT
        
        logger.warning(f"Timeout waiting for SMS (tzid: {tzid})")
        return None
    
    async def set_operation_ok(self, tzid: int) -> bool:
        """
        Mark operation as successful (confirms SMS was used)
        Releases the number
        """
        try:
            await self._request("setOperationOk.php", {'tzid': tzid})
            
            if tzid in self.active_numbers:
                self.active_numbers[tzid].status = NumberStatus.USED
                del self.active_numbers[tzid]
            
            logger.info(f"Marked operation OK for tzid {tzid}")
            return True
        except Exception as e:
            logger.error(f"Error marking operation OK: {e}")
            return False
    
    async def cancel_number(self, tzid: int) -> bool:
        """
        Cancel number order (if SMS not received yet)
        """
        try:
            # Use setOperationRevise to request another SMS or cancel
            await self._request("setOperationRevise.php", {'tzid': tzid})
            
            if tzid in self.active_numbers:
                self.active_numbers[tzid].status = NumberStatus.CANCELLED
                del self.active_numbers[tzid]
            
            logger.info(f"Cancelled number order tzid {tzid}")
            return True
        except Exception as e:
            logger.error(f"Error cancelling number: {e}")
            return False
    
    async def get_number_and_wait_code(
        self,
        service: str = 'telegram',
        country: Optional[str] = None,
        timeout: int = 300
    ) -> Optional[Dict]:
        """
        Convenience method: get number and wait for code
        
        Returns:
            Dict with 'number' and 'code' or None
        """
        try:
            phone = await self.get_number(service, country)
            code = await self.wait_for_code(phone.tzid, timeout)
            
            if code:
                return {
                    'number': phone.number,
                    'code': code,
                    'tzid': phone.tzid,
                    'country': phone.country
                }
            else:
                await self.cancel_number(phone.tzid)
                return None
                
        except OnlineSimError as e:
            logger.error(f"OnlineSim error: {e}")
            return None
    
    async def is_available(self) -> bool:
        """Check if OnlineSim is configured and has balance"""
        if not self.api_key:
            return False
        
        try:
            balance = await self.get_balance()
            return balance > 0
        except:
            return False
    
    def get_active_numbers(self) -> List[PhoneNumber]:
        """Get list of active number orders"""
        return list(self.active_numbers.values())


# Global OnlineSim instance
onlinesim = OnlineSimService()
