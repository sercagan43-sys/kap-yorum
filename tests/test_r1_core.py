import requests
from requests.exceptions import ConnectionError, Timeout

from kap_yorum.engine import KAPYorumEngine
from kap_yorum.kap_client import KAPClient
from kap_yorum.models import (
    CapabilityStatus,
    Company,
    ErrorCategory,
    SourceStatus,
    SystemReadiness,
    get_now_tz,
)


class MockResponse:
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
             # Just matching requests logic closely for testing
             response = requests.Response()
             response.status_code = self.status_code
             raise requests.exceptions.HTTPError(response=response)

class MockHttpClient:
    def __init__(self, post_data=None, get_data=None, fail_post_with=None):
        self.post_data = post_data
        self.get_data = get_data
        self.fail_post_with = fail_post_with
        self.post_call_count = 0

    def post(self, url, **kwargs):
        self.post_call_count += 1
        if self.fail_post_with:
             raise self.fail_post_with
        if self.post_data is not None:
             return MockResponse(self.post_data)
        return MockResponse([])

    def get(self, url, **kwargs):
        if self.get_data is not None:
             return MockResponse(self.get_data)
        return MockResponse([])

# --- Readiness Tests ---
def test_engine_fail_closed_readiness():
    # Default readiness is all NOT_READY
    engine = KAPYorumEngine()
    res = engine.run("ASELS")
    assert "SİSTEM GÜVENLİK KAPANIŞI" in res
    assert "SOURCE_LAYER_NOT_VALIDATED" in res

def test_engine_readiness_override():
    readiness = SystemReadiness(
        ticker_resolution=CapabilityStatus.READY,
        disclosure_listing=CapabilityStatus.READY,
        disclosure_detail=CapabilityStatus.READY
    )
    engine = KAPYorumEngine(http_client=MockHttpClient(get_data=[{"mkkKodu": "ASELS", "unvan": "ASELSAN", "memberOid": "123"}]), readiness=readiness)
    res = engine.run("ASELS")
    # Because client data mock is simplistic in engine integration, it might return empty confirmed
    assert "SİSTEM GÜVENLİK KAPANIŞI" not in res
    assert "Son 30 günlük dönemde KAP açıklaması bulunamadı" in res

# --- Client State & Error Taxonomy Tests ---
def test_kap_client_success():
    now_ms = int(get_now_tz().timestamp() * 1000)
    data = [
        {"disclosureIndex": "123", "publishDate": now_ms, "title": "Test 1"}
    ]
    client = KAPClient(http_client=MockHttpClient(post_data=data))
    company = Company(ticker="ASELS", name="A", member_oid="1")

    discs, metadata = client.get_disclosures(company)
    assert metadata.status == SourceStatus.SUCCESS
    assert metadata.error_category == ErrorCategory.NONE
    assert metadata.records_fetched == 1
    assert metadata.records_failed == 0
    assert discs[0].disclosure_index == "123"

def test_kap_client_empty_confirmed():
    client = KAPClient(http_client=MockHttpClient(post_data=[]))
    company = Company(ticker="ASELS", name="A", member_oid="1")

    discs, metadata = client.get_disclosures(company)
    assert metadata.status == SourceStatus.EMPTY_CONFIRMED
    assert metadata.records_fetched == 0

def test_kap_client_unavailable_timeout():
    mock_client = MockHttpClient(fail_post_with=Timeout("Timeout!"))
    client = KAPClient(http_client=mock_client)
    company = Company(ticker="ASELS", name="A", member_oid="1")

    discs, metadata = client.get_disclosures(company)
    assert metadata.status == SourceStatus.UNAVAILABLE
    assert metadata.error_category == ErrorCategory.TIMEOUT
    # Max retries is 2, so it will call 1 + 2 = 3 times
    assert mock_client.post_call_count == 3
    assert len(discs) == 0

def test_kap_client_unavailable_connection_error():
    mock_client = MockHttpClient(fail_post_with=ConnectionError("Conn Refused"))
    client = KAPClient(http_client=mock_client)
    company = Company(ticker="ASELS", name="A", member_oid="1")

    discs, metadata = client.get_disclosures(company)
    assert metadata.status == SourceStatus.UNAVAILABLE
    assert metadata.error_category == ErrorCategory.CONNECTION_FAILURE

def test_kap_client_invalid_response_schema():
    # API returning dict instead of list
    client = KAPClient(http_client=MockHttpClient(post_data={"error": "Not a list"}))
    company = Company(ticker="ASELS", name="A", member_oid="1")

    discs, metadata = client.get_disclosures(company)
    assert metadata.status == SourceStatus.INVALID_RESPONSE
    assert metadata.error_category == ErrorCategory.SCHEMA_MISMATCH

def test_kap_client_identity_deduplication():
    now_ms = int(get_now_tz().timestamp() * 1000)
    data = [
        {"disclosureIndex": "123", "publishDate": now_ms, "title": "Test 1"},
        {"disclosureIndex": "123", "publishDate": now_ms, "title": "Duplicate"}
    ]
    client = KAPClient(http_client=MockHttpClient(post_data=data))
    company = Company(ticker="ASELS", name="A", member_oid="1")

    discs, metadata = client.get_disclosures(company)
    assert metadata.status == SourceStatus.PARTIAL
    assert metadata.error_category == ErrorCategory.PARTIAL_CHILD_FAILURE
    assert metadata.records_fetched == 1
    assert metadata.records_failed == 1

def test_temporal_timezone_awareness():
    now_ms = int(get_now_tz().timestamp() * 1000)
    data = [
        {"disclosureIndex": "123", "publishDate": now_ms, "title": "Test 1"}
    ]
    client = KAPClient(http_client=MockHttpClient(post_data=data))
    company = Company(ticker="ASELS", name="A", member_oid="1")

    discs, metadata = client.get_disclosures(company)
    assert discs[0].publish_date.tzinfo is not None
