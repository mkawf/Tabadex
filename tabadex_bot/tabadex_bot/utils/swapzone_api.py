# tabadex_bot/utils/swapzone_api.py

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from tabadex_bot.config import logger, settings

API_BASE_URL = "https://api.swapzone.io/v1/exchange"

class SwapZoneAPI:
    """
    A wrapper for the SwapZone API to handle cryptocurrency swaps.
    """
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
        """
        Makes an asynchronous request to the SwapZone API.

        Args:
            method: HTTP method ('GET' or 'POST').
            endpoint: API endpoint (e.g., '/currencies').
            params: URL query parameters.
            data: JSON body for POST requests.

        Returns:
            The JSON response from the API as a dictionary.

        Raises:
            Exception: If the API returns a non-200 status code or request fails.
        """
        session = await self._get_session()
        url = f"{API_BASE_URL}{endpoint}"
        
        # Add API key to all requests
        if params is None:
            params = {}
        params['apiKey'] = self.api_key

        try:
            async with session.request(method, url, params=params, json=data, timeout=20) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"SwapZone API Error: Status {response.status} on {endpoint}. Response: {error_text}")
                    raise Exception(f"API Error: {response.status} - {error_text}")
        except asyncio.TimeoutError:
            logger.error(f"SwapZone API Timeout on endpoint {endpoint}")
            raise Exception("API request timed out.")
        except aiohttp.ClientError as e:
            logger.error(f"SwapZone Client Error on endpoint {endpoint}: {e}")
            raise Exception(f"Network error while contacting API: {e}")

    async def get_currencies(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        Fetches the list of available currencies. Uses a 1-hour cache to avoid frequent calls.
        """
        # Cache valid for 1 hour (3600 seconds)
        if use_cache and self._currencies_cache and (time.time() - self._cache_timestamp < 3600):
            logger.info("Returning currencies from cache.")
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
        """
        Gets the estimated exchange rate, min/max amounts, and other details.

        Returns:
            A dictionary containing rate details. Important keys:
            'amountEstimated', 'min', 'max', 'networkFee', etc.
        """
        params = {
            'from': from_currency,
            'to': to_currency,
            'amount': amount,
        }
        logger.info(f"Getting rate for {amount} {from_currency} to {to_currency}")
        return await self._request('GET', '/rate', params=params)

    async def create_transaction(
        self,
        from_currency: str,
        to_currency: str,
        amount: str,
        recipient_address: str,
        refund_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a new exchange transaction.

        Returns:
            A dictionary containing the new transaction details. Important keys:
            'id', 'depositAddress'.
        """
        data = {
            'from': from_currency,
            'to': to_currency,
            'amount': amount,
            'recipient': recipient_address,
        }
        if refund_address:
            data['refund'] = refund_address

        logger.info(f"Creating transaction: {amount} {from_currency} -> {to_currency}")
        return await self._request('POST', '/create', data=data)

    async def get_transaction_status(self, tx_id: str) -> Dict[str, Any]:
        """
        Fetches the status of an existing transaction.
        """
        params = {'id': tx_id}
        logger.info(f"Getting status for transaction {tx_id}")
        return await self._request('GET', '/tx', params=params)
    
    async def close_session(self):
        """Closes the aiohttp session."""
        if self._session and not self._session.closed:
            await self._session.close()
            logger.info("SwapZone API session closed.")

# Global instance to be used across the application
swapzone_api_client = SwapZoneAPI(api_key=settings.SWAPZONE_API_KEY)