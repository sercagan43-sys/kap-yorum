import requests
from typing import Optional
from kap_yorum.models import Company

class CompanyResolver:
    """
    Validates BIST tickers and resolves them to company details using KAP API.
    """
    KAP_AUTOCOMPLETE_URL = "https://www.kap.org.tr/tr/api/autocomplete"

    def __init__(self, http_client=None):
        self.http_client = http_client or requests

    def resolve(self, ticker: str) -> Optional[Company]:
        if not ticker or not isinstance(ticker, str):
            return None

        ticker = ticker.strip().upper()
        if not ticker:
            return None

        try:
            response = self.http_client.get(self.KAP_AUTOCOMPLETE_URL, timeout=10)
            response.raise_for_status()
            data = response.json()

            for item in data:
                if 'mkkKodu' in item and item['mkkKodu'] == ticker:
                    return Company(
                        ticker=ticker,
                        name=item.get('unvan', ticker),
                        member_oid=item.get('memberOid')
                    )
            return None
        except Exception:
            return None
