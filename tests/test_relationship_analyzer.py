from datetime import timedelta

from kap_yorum.models import AnalysisResult, Disclosure, DisclosureImportance, get_now_tz
from kap_yorum.relationship_analyzer import EventRelationshipAnalyzer


def test_relationship_correction():
    now = get_now_tz()
    d1 = Disclosure(
        disclosure_index="1",
        publish_date=now - timedelta(days=2),
        title="Hata",
        semantic_core="Rutin açıklama",
        importance=DisclosureImportance.MATERIAL,
    )
    d2 = Disclosure(
        disclosure_index="2",
        publish_date=now - timedelta(days=1),
        title="Düzeltme",
        semantic_core="Önceki açıklamanın düzeltilmesi",
        is_correction=True,
    )

    discs = [d1, d2]
    results = {"1": AnalysisResult(disclosure_id="1"), "2": AnalysisResult(disclosure_id="2")}

    analyzer = EventRelationshipAnalyzer()
    analyzer.process_relationships(discs, results)

    assert "DİKKAT" in results["1"].contradictions[0]
    assert d1.importance == DisclosureImportance.LOW_ECONOMIC_VALUE
    assert "Düzeltme hedefi: 1" in results["2"].related_disclosures


def test_relationship_continuation():
    now = get_now_tz()
    d1 = Disclosure(
        disclosure_index="1",
        publish_date=now - timedelta(days=2),
        title="Görüşme",
        semantic_core="Yeni iş bağlantısı/sözleşme",
    )
    d2 = Disclosure(
        disclosure_index="2",
        publish_date=now - timedelta(days=1),
        title="İmza",
        semantic_core="Yeni iş bağlantısı/sözleşme",
    )

    discs = [d1, d2]
    results = {"1": AnalysisResult(disclosure_id="1"), "2": AnalysisResult(disclosure_id="2")}

    analyzer = EventRelationshipAnalyzer()
    analyzer.process_relationships(discs, results)

    assert "Süreç sonucu: 2" in results["1"].related_disclosures
    assert "Devam haberi niteliğinde: 1" in results["2"].related_disclosures


def test_relationship_contradiction_risk():
    now = get_now_tz()
    d1 = Disclosure(
        disclosure_index="1",
        publish_date=now - timedelta(days=2),
        title="Yatırım",
        semantic_core="Kapasite artışı / yeni yatırım",
    )
    d2 = Disclosure(
        disclosure_index="2",
        publish_date=now - timedelta(days=1),
        title="Kredi",
        semantic_core="Finansman / borçlanma",
    )

    discs = [d1, d2]
    results = {"1": AnalysisResult(disclosure_id="1"), "2": AnalysisResult(disclosure_id="2")}

    analyzer = EventRelationshipAnalyzer()
    analyzer.process_relationships(discs, results)

    assert len(results["1"].contradictions) > 0
    assert "Risk Faktörü" in results["1"].contradictions[0]


def test_loop_prevention():
    # Calling process multiple times should not create infinite loops
    # Or recursive references
    now = get_now_tz()
    d1 = Disclosure(
        disclosure_index="1",
        publish_date=now - timedelta(days=2),
        title="Görüşme",
        semantic_core="Yeni iş bağlantısı/sözleşme",
    )
    discs = [d1]
    results = {"1": AnalysisResult(disclosure_id="1")}
    analyzer = EventRelationshipAnalyzer()

    analyzer.process_relationships(discs, results)
    analyzer.process_relationships(discs, results)  # Second call

    # Ensuring logic handles re-runs or isolated nodes gracefully
    assert len(results["1"].related_disclosures) == 0
