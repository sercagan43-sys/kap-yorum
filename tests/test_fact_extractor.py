import pytest
from datetime import datetime
from kap_yorum.models import Disclosure
from kap_yorum.fact_extractor import FactExtractor

def test_extract_facts_basic():
    d = Disclosure(
        disclosure_index="1",
        publish_date=datetime.now(),
        title="Yeni İş İlişkisi",
        content="Şirketimiz ile X arasında 100 milyon TL tutarında sözleşme imzalanmıştır."
    )
    extractor = FactExtractor()
    extractor.extract_facts(d)

    assert len(d.verified_facts) >= 2
    assert "Sözleşme imzalandı." in d.verified_facts
    assert "Tutar/büyüklük bilgisi mevcut." in d.verified_facts

def test_extract_facts_excludes_inferences():
    d = Disclosure(
        disclosure_index="2",
        publish_date=datetime.now(),
        title="Gelecek Beklentileri",
        content="Şirketimizin bu sözleşme ile yüksek kar edeceği beklenmektedir."
    )
    extractor = FactExtractor()
    extractor.extract_facts(d)

    # Should not contain fact about 'kar edecek'
    assert "kar edecek" not in " ".join(d.verified_facts).lower()

def test_extract_facts_empty_content():
    d = Disclosure(
        disclosure_index="3",
        publish_date=datetime.now(),
        title="Boş",
        content=None
    )
    extractor = FactExtractor()
    extractor.extract_facts(d)
    assert len(d.verified_facts) == 0

def test_extract_facts_fallback():
    d = Disclosure(
        disclosure_index="4",
        publish_date=datetime.now(),
        title="Genel Kurul",
        content="Genel kurul toplantısı yapıldı."
    )
    extractor = FactExtractor()
    extractor.extract_facts(d)
    assert len(d.verified_facts) == 1
    assert "Açıklama yapıldı:" in d.verified_facts[0]
