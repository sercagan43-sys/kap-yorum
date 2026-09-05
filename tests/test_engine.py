import pytest
from datetime import datetime
from kap_yorum.engine import KAPYorumEngine
from tests.test_kap_client import MockHttpClient, MockResponse

def test_engine_end_to_end_invalid_ticker():
    # Mocking CompanyResolver failure
    engine = KAPYorumEngine(http_client=MockHttpClient(None))
    result = engine.run("INVALID")
    assert "bulunamadı" in result

def test_engine_end_to_end_no_news():
    # Mocking Company returns, but no news
    class NoNewsHttpClient:
        def get(self, url, timeout):
            if "autocomplete" in url:
                return MockResponse([{"mkkKodu": "ASELS", "unvan": "ASELSAN", "memberOid": "123"}])
            return MockResponse(None)
        def post(self, url, json, timeout):
            return MockResponse([]) # No disclosures

    engine = KAPYorumEngine(http_client=NoNewsHttpClient())
    result = engine.run("ASELS")
    assert "Son 30 günlük dönemde KAP açıklaması bulunamadı" in result

def test_engine_end_to_end_full_flow():
    now = int(datetime.now().timestamp() * 1000)

    class FullFlowHttpClient:
        def get(self, url, timeout):
            if "autocomplete" in url:
                return MockResponse([{"mkkKodu": "ASELS", "unvan": "ASELSAN", "memberOid": "123"}])
            if "Bildirim/111" in url:
                return MockResponse(None, text_data="100 milyon TL tutarında yeni sözleşme imzalanmıştır.")
            if "Bildirim/222" in url:
                return MockResponse(None, text_data="Kapasite artışı için yatırım kararı alınmıştır.")
            if "Bildirim/333" in url:
                 return MockResponse(None, text_data="Yeni kredi anlaşması yapılmıştır.") # Borrowing
            return MockResponse(None, text_data="Rutin bir açıklama.")

        def post(self, url, json, timeout):
            # Return disclosures inside the 30 day window
            return MockResponse([
                {"disclosureIndex": 111, "title": "Yeni İş İlişkisi", "publishDate": now},
                {"disclosureIndex": 222, "title": "Yatırım", "publishDate": now - 100000},
                {"disclosureIndex": 333, "title": "Finansman", "publishDate": now - 50000},
            ])

    engine = KAPYorumEngine(http_client=FullFlowHttpClient())
    result = engine.run("ASELS")

    # Check comprehensive output
    assert "## [ASELS] — SON 30 GÜN KAP DEĞERLENDİRMESİ" in result
    assert "incelenen açıklama: 3" in result
    assert "Yeni iş bağlantısı/sözleşme" in result
    assert "Kapasite artışı / yeni yatırım" in result

    # Check that contradictory risk (Investment + Borrowing) was caught
    assert "Risk Faktörü:" in result

    # Check that unanswered questions are reported with reasons
    assert "Neden:" in result

    # Check that facts vs interpretation are separated structurally (by seeing questions resolved cleanly)
    assert "INSUFFICIENT_PUBLIC_INFORMATION" not in result # The raw enum shouldn't be rendered, only translated questions

    # Ensure it says there is an economic impact
    assert "gelir: " in result
