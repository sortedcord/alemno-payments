import httpx
import redis
from app.core.config import settings
from app.core.logging import logger


class ExchangeRateClient:
    def __init__(self):
        self.default_rate = 93.0
        self.cache_key = "usd_to_inr_rate"
        self.cache_ttl = 86400  # 24 hours cache duration
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
            )
        except Exception as e:
            logger.warning(f"Could not connect to Redis for exchange rate caching: {e}")
            self.redis_client = None

    async def get_usd_to_inr_rate(self) -> float:
        """
        Retrieves the USD to INR conversion rate.
        Checks Redis cache first. If cache is empty/offline, fetches from a free public API
        and updates the cache. Falls back to a hardcoded default rate if both fail.
        """
        # read from cache
        if self.redis_client:
            try:
                cached_rate = self.redis_client.get(self.cache_key)
                if cached_rate:
                    logger.info("Retrieved exchange rate from Redis cache.")
                    return float(cached_rate)
            except Exception as e:
                logger.warning(f"Failed to read exchange rate from Redis: {e}")

        # fetching from Exchange Rate API
        try:
            logger.info("Fetching live exchange rate from API...")
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get("https://open.er-api.com/v6/latest/USD")
                if response.status_code == 200:
                    data = response.json()
                    rates = data.get("rates", {})
                    inr_rate = rates.get("INR")
                    if inr_rate:
                        inr_rate = float(inr_rate)
                        logger.info(
                            f"Successfully fetched live exchange rate: {inr_rate}"
                        )
                        # Cache the rate in Redis
                        if self.redis_client:
                            try:
                                self.redis_client.set(
                                    self.cache_key, str(inr_rate), ex=self.cache_ttl
                                )
                            except Exception as ce:
                                logger.warning(
                                    f"Failed to cache exchange rate in Redis: {ce}"
                                )
                        return inr_rate
        except Exception as e:
            logger.error(
                f"Error fetching live exchange rate: {e}. Falling back to default rate {self.default_rate}"
            )

        # 3. Fallback
        return self.default_rate
