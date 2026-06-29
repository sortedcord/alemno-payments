import pytest
from app.clients.exchange_rate_client import ExchangeRateClient

pytestmark = pytest.mark.asyncio


async def test_get_usd_to_inr_rate():
    client = ExchangeRateClient()
    rate = await client.get_usd_to_inr_rate()
    assert isinstance(rate, float)
    # The rate should be positive (either the fetched rate or the default fallback of 83.0)
    assert rate > 0.0
