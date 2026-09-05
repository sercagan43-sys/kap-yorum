from kap_yorum.economic_analyzer import EconomicAnalyzer
from kap_yorum.models import (
    Disclosure,
    DisclosureImportance,
    EconomicQuestion,
    QuestionStatus,
    get_now_tz,
)


def test_analyze_low_value():
    d = Disclosure(
        disclosure_index="1",
        publish_date=get_now_tz(),
        title="Test",
        importance=DisclosureImportance.LOW_ECONOMIC_VALUE,
    )
    analyzer = EconomicAnalyzer()
    result = analyzer.analyze(d, [])
    assert result.impact.revenue is None
    assert result.impact.profitability is None


def test_analyze_contract():
    d = Disclosure(
        disclosure_index="2",
        publish_date=get_now_tz(),
        title="Test",
        importance=DisclosureImportance.CRITICAL,
        semantic_core="Yeni iş bağlantısı/sözleşme",
    )
    questions = [EconomicQuestion(question="Test", status=QuestionStatus.ANSWERED)]
    analyzer = EconomicAnalyzer()
    result = analyzer.analyze(d, questions)

    assert "gelir artışı" in result.impact.revenue.lower()
    assert "bilinememektedir" in result.impact.profitability.lower()
    assert result.impact.debt_financing == "NOT_APPLICABLE"


def test_analyze_not_applicable():
    d = Disclosure(
        disclosure_index="3",
        publish_date=get_now_tz(),
        title="Test",
        importance=DisclosureImportance.MATERIAL,
        semantic_core="Bilinmeyen olay türü",
    )
    analyzer = EconomicAnalyzer()
    result = analyzer.analyze(d, [])

    assert result.impact.revenue == "NOT_APPLICABLE"
    assert result.impact.profitability == "NOT_APPLICABLE"
    assert result.impact.debt_financing == "NOT_APPLICABLE"
