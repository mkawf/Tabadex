# tabadex_bot/utils/swapzone_api.py

import asyncio
import time
from typing import Any, Dict, List, Optional

import aiohttp
from ..config import logger, settings

API_BASE_URL = "https://api.swapzone.io/v1/exchange"

class SwapZoneAPI:
    """A wrapper for the SwapZone API to handle cryptocurrency swaps."""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self._session: aiohttp.ClientSession | None = None
        self._currencies_cache: List[Dict[str, Any]] = []
        self._cache_timestamp: float = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        """Initializes and returns the aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Makes an asynchronous request to the SwapZone API with detailed error logging."""
        session = await self._get_session()
        url = f"{API_BASE_URL}{endpoint}"
        
        headers = {
            'x-api-key': self.api_key
        }

        try:
            async with session.request(method, url, params=params, json=data, headers=headers, timeout=15) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(
                        f"SwapZone API Error on endpoint '{endpoint}'. "
                        f"Status: {response.status}, "
                        f"Reason: {response.reason}, "
                        f"Response: {error_text}"
                    )
                    raise Exception(f"API request failed with status {response.status}")
                
                return await response.json()

        except asyncio.TimeoutError:
            logger.error(f"SwapZone API Timeout on endpoint '{endpoint}' after 15 seconds.")
            raise Exception("API request timed out.")
        except aiohttp.ClientConnectorError as e:
            logger.error(f"SwapZone API Connection Error on endpoint '{endpoint}': {e}")
            raise Exception(f"Network connection error: Unable to connect to API endpoint.")
        except Exception as e:
            logger.error(f"An unexpected error occurred during API request to '{endpoint}': {e}")
            raise e


    async def get_currencies(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Fetches the list of available currencies."""
        if use_cache and self._currencies_cache and (time.time() - self._cache_timestamp < 3600):
            return self._currencies_cache

        logger.info("Fetching currencies from SwapZone API...")
        response = await self._request('GET', '/currencies')
        if isinstance(response, list):
            self._currencies_cache = response
            self._cache_timestamp = time.time()
            return response
        else:
            logger.error(f"Unexpected response format for /currencies: {response}")
            raise Exception("Failed to parse currencies from API.")

    async def get_rate(self, from_currency: str, to_currency: str, amount: str) -> Dict[str, Any]:
        """Gets the estimated exchange rate with additional required parameters."""
        # --- <<< بخش اصلاح شده و حیاتی اینجاست >>> ---
        # اضافه کردن پارامترهای جدید طبق راهنمایی پشتیبانی
        params = {
            'from': from_currency,
            'to': to_currency,
            'amount': amount,
            'rateType': 'all',        # برای جستجو در تمام شرکای تبادل
            'chooseRate': 'best',     # برای انتخاب بهترین نرخ
        }
        logger.info(f"Getting rate for {amount} {from_currency} to {to_currency} with extended params")
        return await self._request('GET', '/rate', params=params)

    async def create_transaction(self, from_currency: str, to_currency: str, amount: str, recipient: str, refund: Optional[str] = None) -> Dict[str, Any]:
        """Creates a new exchange transaction."""
        data = {
            'from': from_currency, 'to': to_currency, 'amount': amount,
            'recipient': recipient, 'refund': refund
        }
        logger.info(f"Creating transaction: {amount} {from_currency} -> {to_currency}")
        return await self._request('POST', '/create', data=data)

    async def get_transaction_status(self, tx_id: str) -> Dict[str, Any]:
        """Fetches the status of an existing transaction."""
        params = {'id': tx_id}
        logger.info(f"Getting status for transaction {tx_id}")
        return await self._request('GET', '/tx', params=params)
    
    async def close_session(self):
        """Closes the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("SwapZone API session closed.")

swapzone_api_client = SwapZoneAPI(api_key=settings.SWAPZONE_API_KEY)