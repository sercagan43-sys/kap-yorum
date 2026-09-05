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
    class TestEngine(KAPYorumEngine):
        def set_readiness(self, r: SystemReadiness) -> None:
            self._readiness = r

    readiness = SystemReadiness(
        ticker_resolution=CapabilityStatus.READY,
        disclosure_listing=CapabilityStatus.READY,
        disclosure_detail=CapabilityStatus.READY,
    )
    engine = TestEngine(
        http_client=MockHttpClient(
            get_data=[{"mkkKodu": "ASELS", "unvan": "ASELSAN", "memberOid": "123"}]
        )
    )
    engine.set_readiness(readiness)
    res = engine.run("ASELS")
    # Because client data mock is simplistic in engine integration, it might return empty confirmed
    assert "SİSTEM GÜVENLİK KAPANIŞI" not in res
    assert "Son 30 günlük dönemde KAP açıklaması bulunamadı" in res


def test_production_readiness_manual_bypass_attempt():
    engine = KAPYorumEngine(http_client=MockHttpClient())
    res = engine.run("ASELS")
    assert "SİSTEM GÜVENLİK KAPANIŞI" in res


# --- Client State & Error Taxonomy Tests ---
def test_kap_client_success():
    now_ms = int(get_now_tz().timestamp() * 1000)
    data = [{"disclosureIndex": "123", "publishDate": now_ms, "title": "Test 1"}]
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
        {"disclosureIndex": "123", "publishDate": now_ms, "title": "Duplicate"},
    ]
    client = KAPClient(http_client=MockHttpClient(post_data=data))
    company = Company(ticker="ASELS", name="A", member_oid="1")

    discs, metadata = client.get_disclosures(company)
    assert metadata.status == SourceStatus.PARTIAL
    assert metadata.error_category == ErrorCategory.DUPLICATE_IDENTIFIER
    assert metadata.records_fetched == 1
    assert metadata.records_failed == 1


def test_kap_client_missing_canonical_id():
    now_ms = int(get_now_tz().timestamp() * 1000)
    data = [
        {"disclosureIndex": "123", "publishDate": now_ms, "title": "Test 1"},
        {"disclosureIndex": "", "publishDate": now_ms, "title": "Missing ID"},
    ]
    client = KAPClient(http_client=MockHttpClient(post_data=data))
    company = Company(ticker="ASELS", name="A", member_oid="1")

    discs, metadata = client.get_disclosures(company)
    assert metadata.status == SourceStatus.PARTIAL
    assert metadata.error_category == ErrorCategory.MISSING_IDENTIFIER
    assert metadata.records_fetched == 1
    assert metadata.records_failed == 1


def test_kap_client_multiple_errors_batch():
    now_ms = int(get_now_tz().timestamp() * 1000)
    data = [
        {"disclosureIndex": "123", "publishDate": now_ms, "title": "Test 1"},
        {"disclosureIndex": "123", "publishDate": now_ms, "title": "Duplicate"},
        {"disclosureIndex": "124", "publishDate": "not-a-date", "title": "Invalid Date"},
    ]
    client = KAPClient(http_client=MockHttpClient(post_data=data))
    company = Company(ticker="ASELS", name="A", member_oid="1")

    discs, metadata = client.get_disclosures(company)
    assert metadata.status == SourceStatus.PARTIAL
    assert metadata.error_category == ErrorCategory.MULTIPLE_ERRORS
    assert metadata.records_fetched == 1
    assert metadata.records_failed == 2


def test_metadata_invariant_success_with_error():
    import pytest

    from kap_yorum.models import RequestMetadata

    now = get_now_tz()

    with pytest.raises(ValueError, match="must have ErrorCategory.NONE"):
        RequestMetadata(
            source_name="Test",
            operation_name="Test",
            start_time=now,
            status=SourceStatus.SUCCESS,
            error_category=ErrorCategory.HTTP_ERROR,
        )


def test_metadata_invariant_unavailable_with_none():
    import pytest

    from kap_yorum.models import RequestMetadata

    now = get_now_tz()

    with pytest.raises(ValueError, match="cannot have ErrorCategory.NONE"):
        RequestMetadata(
            source_name="Test",
            operation_name="Test",
            start_time=now,
            status=SourceStatus.UNAVAILABLE,
            error_category=ErrorCategory.NONE,
        )


def test_metadata_invariant_invalid_response_with_none():
    import pytest

    from kap_yorum.models import RequestMetadata

    now = get_now_tz()

    with pytest.raises(ValueError, match="cannot have ErrorCategory.NONE"):
        RequestMetadata(
            source_name="Test",
            operation_name="Test",
            start_time=now,
            status=SourceStatus.INVALID_RESPONSE,
            error_category=ErrorCategory.NONE,
        )


def test_temporal_timezone_awareness():
    now_ms = int(get_now_tz().timestamp() * 1000)
    data = [{"disclosureIndex": "123", "publishDate": now_ms, "title": "Test 1"}]
    client = KAPClient(http_client=MockHttpClient(post_data=data))
    company = Company(ticker="ASELS", name="A", member_oid="1")

    discs, metadata = client.get_disclosures(company)
    assert discs[0].publish_date.tzinfo is not None


def test_missing_publish_date():
    data = [{"disclosureIndex": "123", "title": "Test 1"}]
    client = KAPClient(http_client=MockHttpClient(post_data=data))
    company = Company(ticker="ASELS", name="A", member_oid="1")

    discs, metadata = client.get_disclosures(company)
    assert metadata.status == SourceStatus.INVALID_RESPONSE
    assert metadata.error_category == ErrorCategory.SCHEMA_MISMATCH
    assert metadata.records_failed == 1
    assert len(discs) == 0


def test_malformed_publish_date():
    data = [{"disclosureIndex": "123", "publishDate": "not-a-date", "title": "Test 1"}]
    client = KAPClient(http_client=MockHttpClient(post_data=data))
    company = Company(ticker="ASELS", name="A", member_oid="1")

    discs, metadata = client.get_disclosures(company)
    assert metadata.status == SourceStatus.INVALID_RESPONSE
    assert metadata.error_category == ErrorCategory.SCHEMA_MISMATCH
    assert metadata.records_failed == 1
    assert len(discs) == 0


def test_partial_valid_invalid_date():
    now_ms = int(get_now_tz().timestamp() * 1000)
    data = [
        {"disclosureIndex": "123", "publishDate": now_ms, "title": "Valid"},
        {"disclosureIndex": "124", "publishDate": "not-a-date", "title": "Invalid"},
    ]
    client = KAPClient(http_client=MockHttpClient(post_data=data))
    company = Company(ticker="ASELS", name="A", member_oid="1")

    discs, metadata = client.get_disclosures(company)
    assert metadata.status == SourceStatus.PARTIAL
    assert metadata.error_category == ErrorCategory.SCHEMA_MISMATCH
    assert metadata.records_failed == 1
    assert len(discs) == 1


def test_unknown_error_invariant():
    class UnknownErrorHttpClient:
        def post(self, url, **kwargs):
            raise ValueError("Something completely unexpected")

    client = KAPClient(http_client=UnknownErrorHttpClient())
    company = Company(ticker="ASELS", name="A", member_oid="1")

    discs, metadata = client.get_disclosures(company)
    assert metadata.status == SourceStatus.UNAVAILABLE
    assert metadata.error_category == ErrorCategory.UNKNOWN_ERROR


def test_http_status_codes():
    company = Company(ticker="ASELS", name="A", member_oid="1")

    # 400 Bad Request -> HTTP_ERROR
    class HTTP400Client:
        def __init__(self):
            self.calls = 0

        def post(self, url, **kwargs):
            self.calls += 1
            resp = requests.Response()
            resp.status_code = 400
            raise requests.exceptions.HTTPError(response=resp)

    mock400 = HTTP400Client()
    client = KAPClient(http_client=mock400)
    _, metadata = client.get_disclosures(company)
    assert metadata.error_category == ErrorCategory.HTTP_ERROR
    assert mock400.calls == 1  # 400 is not retryable

    # 401 Unauthorized -> AUTH_ERROR
    class HTTP401Client:
        def post(self, url, **kwargs):
            resp = requests.Response()
            resp.status_code = 401
            raise requests.exceptions.HTTPError(response=resp)

    client = KAPClient(http_client=HTTP401Client())
    _, metadata = client.get_disclosures(company)
    assert metadata.error_category == ErrorCategory.AUTH_ERROR

    # 429 Too Many Requests -> RATE_LIMIT
    class HTTP429Client:
        def post(self, url, **kwargs):
            resp = requests.Response()
            resp.status_code = 429
            raise requests.exceptions.HTTPError(response=resp)

    client = KAPClient(http_client=HTTP429Client())
    _, metadata = client.get_disclosures(company)
    assert metadata.error_category == ErrorCategory.RATE_LIMIT

    class HTTP500Client:
        def __init__(self):
            self.calls = 0

        def post(self, url, **kwargs):
            self.calls += 1
            resp = requests.Response()
            resp.status_code = 500
            raise requests.exceptions.HTTPError(response=resp)

    mock500 = HTTP500Client()
    client = KAPClient(http_client=mock500)
    _, metadata = client.get_disclosures(company)
    assert metadata.error_category == ErrorCategory.HTTP_ERROR
    assert mock500.calls == 3  # 1 initial + 2 retries


def test_malformed_json_response():
    class MalformedJSONClient:
        def post(self, url, **kwargs):
            resp = requests.Response()
            resp.status_code = 200

            # Mocking the behavior where json() raises an error
            def raise_json_error():
                raise requests.exceptions.JSONDecodeError("Expecting value", "", 0)

            resp.json = raise_json_error
            return resp

    client = KAPClient(http_client=MalformedJSONClient())
    company = Company(ticker="ASELS", name="A", member_oid="1")
    discs, metadata = client.get_disclosures(company)

    assert metadata.status == SourceStatus.INVALID_RESPONSE
    assert metadata.error_category == ErrorCategory.MALFORMED_RESPONSE


def test_naive_datetime_rejection():
    from datetime import datetime

    import pytest

    from kap_yorum.models import Disclosure, DisclosureImportance, RequestMetadata

    # naive datetime
    naive_dt = datetime(2025, 1, 1, 12, 0)
    with pytest.raises(ValueError, match="timezone-aware"):
        RequestMetadata(
            source_name="Test",
            operation_name="Test",
            start_time=naive_dt,
            status=SourceStatus.SUCCESS,
        )

    with pytest.raises(ValueError, match="timezone-aware"):
        Disclosure(
            disclosure_index="123",
            publish_date=naive_dt,
            title="Test",
            importance=DisclosureImportance.CRITICAL,
        )


def test_conflicting_identity_behavior():
    now_ms = int(get_now_tz().timestamp() * 1000)
    # Different titles, but same canonical ID (disclosureIndex)
    data = [
        {"disclosureIndex": "123", "publishDate": now_ms, "title": "First Version"},
        {"disclosureIndex": "123", "publishDate": now_ms, "title": "Second Version"},
    ]
    client = KAPClient(http_client=MockHttpClient(post_data=data))
    company = Company(ticker="ASELS", name="A", member_oid="1")

    discs, metadata = client.get_disclosures(company)
    assert metadata.status == SourceStatus.PARTIAL
    assert metadata.error_category == ErrorCategory.DUPLICATE_IDENTIFIER
    assert metadata.records_fetched == 1
    assert metadata.records_failed == 1
    # Check that it kept the first one and rejected the conflicting identity
    assert discs[0].title == "First Version"
