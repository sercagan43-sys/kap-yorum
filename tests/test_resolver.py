import pytest
from kap_yorum.resolver import CompanyResolver

class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception("HTTP Error")

class MockHttpClient:
    def __init__(self, data):
        self.data = data
        self.called_url = None

    def get(self, url, timeout):
        self.called_url = url
        if self.data is None:
            raise Exception("Network error")
        return MockResponse(self.data)

def test_resolve_valid_ticker():
    mock_data = [
        {"mkkKodu": "ASELS", "unvan": "ASELSAN ELEKTRONIK", "memberOid": "123"}
    ]
    resolver = CompanyResolver(http_client=MockHttpClient(mock_data))
    company = resolver.resolve("ASELS")
    assert company is not None
    assert company.ticker == "ASELS"
    assert company.name == "ASELSAN ELEKTRONIK"
    assert company.member_oid == "123"

def test_resolve_lowercase_ticker():
    mock_data = [
        {"mkkKodu": "ASELS", "unvan": "ASELSAN ELEKTRONIK", "memberOid": "123"}
    ]
    resolver = CompanyResolver(http_client=MockHttpClient(mock_data))
    company = resolver.resolve("asels")
    assert company is not None
    assert company.ticker == "ASELS"

def test_resolve_whitespace_ticker():
    mock_data = [
        {"mkkKodu": "ASELS", "unvan": "ASELSAN ELEKTRONIK", "memberOid": "123"}
    ]
    resolver = CompanyResolver(http_client=MockHttpClient(mock_data))
    company = resolver.resolve("  ASELS  ")
    assert company is not None
    assert company.ticker == "ASELS"

def test_resolve_invalid_ticker():
    mock_data = [
        {"mkkKodu": "ASELS", "unvan": "ASELSAN ELEKTRONIK", "memberOid": "123"}
    ]
    resolver = CompanyResolver(http_client=MockHttpClient(mock_data))
    company = resolver.resolve("INVALID")
    assert company is None

def test_resolve_network_error():
    resolver = CompanyResolver(http_client=MockHttpClient(None))
    company = resolver.resolve("ASELS")
    assert company is None

def test_resolve_empty_ticker():
    resolver = CompanyResolver(http_client=MockHttpClient([]))
    assert resolver.resolve("") is None
    assert resolver.resolve("   ") is None
    assert resolver.resolve(None) is None
