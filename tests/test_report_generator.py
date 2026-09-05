from kap_yorum.models import (
    AnalysisResult,
    Disclosure,
    DisclosureImportance,
    EconomicQuestion,
    QuestionStatus,
    get_now_tz,
)
from kap_yorum.report_generator import ReportGenerator


def test_generate_empty():
    generator = ReportGenerator()
    report = generator.generate("ASELS", [], {})
    assert "bulunamadı" in report.general_evaluation

    md = generator.render_markdown(report)
    assert "bulunamadı" in md
    assert "Kapsam" not in md


def test_generate_full():
    d = Disclosure(
        disclosure_index="1",
        publish_date=get_now_tz(),
        title="Test",
        importance=DisclosureImportance.CRITICAL,
        semantic_core="Test Core",
        real_value_point="Test Value",
    )

    res = AnalysisResult(
        disclosure_id="1",
        questions=[
            EconomicQuestion(
                question="Why?", status=QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION, reason="Sır"
            )
        ],
        contradictions=["Risk 1"],
    )

    generator = ReportGenerator()
    report = generator.generate("ASELS", [d], {"1": res})

    assert report.critical_count == 1
    assert len(report.unanswered_questions) == 1
    assert len(report.negative_risky_findings) == 1

    md = generator.render_markdown(report)
    assert "## [ASELS]" in md
    assert "Kapsam" in md
    assert "Why? -> Neden: Sır" in md
    assert "Risk 1" in md
