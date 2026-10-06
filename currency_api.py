from datetime import datetime, timezone

import httpx2 as httpx


RATES_URL = "https://open.er-api.com/v6/latest/USD"


async def fetch_rates():
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(RATES_URL)
        response.raise_for_status()
        payload = response.json()

    rates = payload.get("rates")
    if payload.get("result") != "success" or not isinstance(rates, dict):
        raise ValueError("The exchange-rate service returned an unexpected response")
    needed = {code: float(rates[code]) for code in ("USD", "UZS", "RUB", "KRW") if code in rates}
    if len(needed) < 4:
        raise ValueError("The exchange-rate service did not provide all supported currencies")
    return {
        "rates": needed,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
