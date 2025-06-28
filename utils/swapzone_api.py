# tabadex_bot/utils/swapzone_api.py

import asyncio
import time
from typing import Any, Dict, List, Optional

import aiohttp
from ..config import logger, settings

API_BASE_URL = "https://api.swapzone.io/v1/exchange"

class SwapZoneAPI:
    """A wrapper for the SwapZone API to handle cryptocurrency swaps."""
    def __init__(self, api_key: str, max_retries: int = 3):
        self.api_key = api_key
        self.max_retries = max_retries
        self._session: aiohttp.ClientSession | None = None
        self._currencies_cache: List[Dict[str, Any]] = []
        self._cache_timestamp: float = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers = {'x-api-key': self.api_key}
            self._session = aiohttp.ClientSession(headers=headers)
        return self._session

    async def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        session = await self._get_session()
        url = f"{API_BASE_URL}{endpoint}"

        for attempt in range(1, self.max_retries + 1):
            try:
                async with session.request(method, url, params=params, json=data, timeout=20) as response:
                    text_response = await response.text()

                    if response.status == 200:
                        return await response.json()

                    # Log warning and retry if status in transient errors
                    if response.status in {500, 502, 503, 504}:
                        logger.warning(f"Transient error on {endpoint}. Status: {response.status}, Attempt {attempt}/{self.max_retries}")
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue

                    # For 4xx errors, raise a descriptive exception
                    logger.error(f"SwapZone API Error on '{endpoint}'. Status: {response.status}, Response: {text_response}")
                    raise Exception(f"API request failed ({response.status}): {text_response}")

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"Network error on '{endpoint}'. Attempt {attempt}/{self.max_retries}: {e}")
                await asyncio.sleep(2 ** attempt)

        # If we reach here → all retries failed
        logger.error(f"SwapZone API request failed after {self.max_retries} attempts → endpoint: {endpoint}")
        raise Exception(f"SwapZone API request failed after {self.max_retries} attempts")

    async def get_currencies(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        if use_cache and self._currencies_cache and (time.time() - self._cache_timestamp < 3600):
            return self._currencies_cache

        logger.info("Fetching currencies from SwapZone API...")
        response = await self._request('GET', '/currencies')

        if isinstance(response, list):
            self._currencies_cache = [c for c in response if c.get('ticker')]
            self._cache_timestamp = time.time()
            return self._currencies_cache

        raise Exception("Failed to parse currencies from API.")

    async def get_rate(self, from_currency: str, from_network: str, to_currency: str, to_network: str, amount: str) -> Dict[str, Any]:
        """Gets the estimated exchange rate with ALL required parameters."""
        params = {
            'from': from_currency,
            'fromNetwork': from_network,
            'to': to_currency,
            'toNetwork': to_network,
            'amount': amount,
            'rateType': 'all',
        }
        logger.info(f"Getting rate with full params: {params}")
        return await self._request('GET', '/rate', params=params)

    async def create_transaction(self, **kwargs) -> Dict[str, Any]:
        logger.info(f"Creating transaction with data: {kwargs}")
        return await self._request('POST', '/create', data=kwargs)

    async def close_session(self):
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("SwapZone API session closed.")

swapzone_api_client = SwapZoneAPI(api_key=settings.SWAPZONE_API_KEY)
