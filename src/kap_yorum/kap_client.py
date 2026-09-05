import requests
from datetime import datetime, timedelta
from typing import List, Optional
from kap_yorum.models import Disclosure, Company

class KAPClient:
    """
    Fetches disclosures for a given company from KAP within a maximum 30-day window.
    """
    KAP_DISCLOSURE_LIST_URL = "https://www.kap.org.tr/tr/api/memberDisclosureQuery"
    KAP_DISCLOSURE_DETAIL_URL = "https://www.kap.org.tr/tr/bildirim-sorgu" # This is a placeholder for actual detail logic

    def __init__(self, http_client=None):
        self.http_client = http_client or requests

    def get_disclosures(self, company: Company, max_days: int = 30) -> List[Disclosure]:
        if not company or not company.member_oid:
            return []

        now = datetime.now()
        start_date = now - timedelta(days=max_days)

        # Format for KAP API (YYYY-MM-DD)
        from_date_str = start_date.strftime("%Y-%m-%d")
        to_date_str = now.strftime("%Y-%m-%d")

        payload = {
            "fromDate": from_date_str,
            "toDate": to_date_str,
            "year": "",
            "prd": "",
            "term": "",
            "ruleType": "",
            "bdkReview": "",
            "disclosureClass": "",
            "index": "",
            "market": "",
            "isLate": "",
            "subjectList": [],
            "mkkMemberOidList": [company.member_oid],
            "inactiveMkkMemberOidList": [],
            "bdkMemberOidList": [],
            "mainSector": "",
            "sector": "",
            "subSector": "",
            "memberType": "IGS",
            "fromSrc": "True",
            "srcCategory": "",
            "discIndex": []
        }

        try:
            response = self.http_client.post(
                self.KAP_DISCLOSURE_LIST_URL,
                json=payload,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
        except Exception as e:
            # Re-raise to distinguish network failure from empty news list
            raise ConnectionError("KAP listesi alınırken erişim hatası oluştu.") from e

        disclosures = []
        for item in data:
            # The API returns timestamp in milliseconds sometimes, but KAP standard query returns objects
            publish_date = datetime.fromtimestamp(item.get('publishDate', 0) / 1000.0) if isinstance(item.get('publishDate'), (int, float)) else now

            # If date format is string, we'll need to parse it (simplified for now)
            if isinstance(item.get('publishDate'), str):
                 try:
                     # e.g. '2024-05-15 14:30:00'
                     publish_date = datetime.strptime(item['publishDate'], "%Y-%m-%d %H:%M:%S")
                 except:
                     publish_date = now

            if publish_date < start_date:
                continue

            disc_index = str(item.get('disclosureIndex', ''))

            disclosure = Disclosure(
                disclosure_index=disc_index,
                publish_date=publish_date,
                title=item.get('title', 'No Title'),
                url=f"https://www.kap.org.tr/tr/Bildirim/{disc_index}" if disc_index else None
            )

            # Fetch full content
            self._fetch_content(disclosure)

            disclosures.append(disclosure)

        return disclosures

    def _fetch_content(self, disclosure: Disclosure) -> None:
        if not disclosure.disclosure_index:
            return

        # Simplified content fetcher for KAP (HTML scraping or specific API)
        # Note: True KAP fetching is complex (HTML parsing, PDF extraction, etc.)
        # For this prototype, we'll mock or make a basic HTTP GET and extract text
        try:
             url = f"https://www.kap.org.tr/tr/Bildirim/{disclosure.disclosure_index}"
             response = self.http_client.get(url, timeout=10)
             if response.status_code == 200:
                 # Very simplified HTML extraction
                 text = response.text
                 # Just dump the HTML or a slice of it for now
                 # In a real app we'd use BeautifulSoup
                 disclosure.content = text[:1000] # truncate for safety in prototype
             else:
                 disclosure.content = None
        except Exception:
             disclosure.content = None
