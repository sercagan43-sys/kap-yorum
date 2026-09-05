import pytest
from kap_yorum.models import QuestionStatus, DisclosureImportance, Company, Disclosure

def test_models():
    company = Company(ticker="ASELS", name="Aselsan")
    assert company.ticker == "ASELS"

    assert QuestionStatus.ANSWERED == "ANSWERED"
    assert DisclosureImportance.CRITICAL == "CRITICAL"
