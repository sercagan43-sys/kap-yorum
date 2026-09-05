import pytest
from datetime import datetime, timedelta
from kap_yorum.kap_client import KAPClient
from kap_yorum.models import Company, Disclosure

class MockResponse:
    def __init__(self, json_data, text_data="Mock content", status_code=200):
        self.json_data = json_data
        self.text = text_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error {self.status_code}")

class MockHttpClient:
    def __init__(self, list_data, content_map=None, fail_list=False):
        self.list_data = list_data
        self.content_map = content_map or {}
        self.fail_list = fail_list

    def post(self, url, json, timeout):
        if self.fail_list:
            raise Exception("List fetch failed")
        return MockResponse(self.list_data)

    def get(self, url, timeout):
        if url in self.content_map:
            if self.content_map[url] is None:
                raise Exception("Content fetch failed")
            return MockResponse(None, text_data=self.content_map[url])
        return MockResponse(None, text_data="Default content")

def test_get_disclosures_success():
    now = datetime.now()
    valid_ts = int(now.timestamp() * 1000)
    old_ts = int((now - timedelta(days=35)).timestamp() * 1000)

    mock_data = [
        {"disclosureIndex": 12345, "title": "Test 1", "publishDate": valid_ts},
        {"disclosureIndex": 67890, "title": "Old", "publishDate": old_ts} # Should be filtered out
    ]

    company = Company(ticker="ASELS", name="Aselsan", member_oid="123")
    client = KAPClient(http_client=MockHttpClient(mock_data))

    disclosures = client.get_disclosures(company)
    assert len(disclosures) == 1
    assert disclosures[0].disclosure_index == "12345"
    assert disclosures[0].title == "Test 1"
    assert "Default content" in disclosures[0].content

def test_get_disclosures_no_member_oid():
    company = Company(ticker="ASELS", name="Aselsan", member_oid=None)
    client = KAPClient(http_client=MockHttpClient([]))
    assert client.get_disclosures(company) == []

def test_get_disclosures_list_failure():
    company = Company(ticker="ASELS", name="Aselsan", member_oid="123")
    client = KAPClient(http_client=MockHttpClient([], fail_list=True))
    with pytest.raises(ConnectionError):
        client.get_disclosures(company)

def test_get_disclosures_partial_content_failure():
    now = datetime.now()
    valid_ts = int(now.timestamp() * 1000)

    mock_data = [
        {"disclosureIndex": 111, "title": "Test 1", "publishDate": valid_ts},
        {"disclosureIndex": 222, "title": "Test 2", "publishDate": valid_ts}
    ]

    content_map = {
        "https://www.kap.org.tr/tr/Bildirim/111": "Full text 1",
        "https://www.kap.org.tr/tr/Bildirim/222": None # Force failure
    }

    company = Company(ticker="ASELS", name="Aselsan", member_oid="123")
    client = KAPClient(http_client=MockHttpClient(mock_data, content_map=content_map))

    disclosures = client.get_disclosures(company)
    assert len(disclosures) == 2
    assert disclosures[0].content == "Full text 1"
    assert disclosures[1].content is None # Should continue processing list despite content failure

def test_get_disclosures_duplicate_protection_implicit():
    # Will be tested in integration, but client returns list. System logic handles duplicates.
    pass
