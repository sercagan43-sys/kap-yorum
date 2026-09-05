from kap_yorum.models import Company, DisclosureImportance, QuestionStatus


def test_models():
    company = Company(ticker="ASELS", name="Aselsan")
    assert company.ticker == "ASELS"

    assert QuestionStatus.ANSWERED == "ANSWERED"
    assert DisclosureImportance.CRITICAL == "CRITICAL"
