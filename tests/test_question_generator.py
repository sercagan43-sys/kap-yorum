from kap_yorum.models import Disclosure, DisclosureImportance, QuestionStatus
from kap_yorum.question_generator import QuestionGenerator


def test_no_questions_for_low_value():
    d = Disclosure(
        disclosure_index="1",
        publish_date="2023-01-01",
        title="Test",
        importance=DisclosureImportance.LOW_ECONOMIC_VALUE
    )
    generator = QuestionGenerator()
    questions = generator.generate_and_resolve(d)
    assert len(questions) == 0

def test_contract_questions_resolution():
    d = Disclosure(
        disclosure_index="2",
        publish_date="2023-01-01",
        title="Test",
        content="100 milyon TL sözleşme imzalanmıştır.",
        importance=DisclosureImportance.CRITICAL,
        semantic_core="Yeni iş bağlantısı/sözleşme",
        verified_facts=["Tutar bilgisi mevcut", "Sözleşme imzalandı"]
    )
    generator = QuestionGenerator()
    questions = generator.generate_and_resolve(d)

    assert len(questions) == 5

    # Check Kesinleşmiş mi?
    q_kesin = next(q for q in questions if q.question == "Kesinleşmiş mi?")
    assert q_kesin.status == QuestionStatus.ANSWERED

    # Check Tutarı ne?
    q_tutar = next(q for q in questions if q.question == "Tutarı ne?")
    assert q_tutar.status == QuestionStatus.ANSWERED

    # Check Karlılık
    q_kar = next(q for q in questions if q.question == "Kârlılık hakkında yeterli bilgi var mı?")
    assert q_kar.status == QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION
    assert q_kar.reason is not None

def test_missing_reason_safety_catch():
    d = Disclosure(
        disclosure_index="3",
        publish_date="2023-01-01",
        title="Test",
        importance=DisclosureImportance.MATERIAL,
        semantic_core="Bilinmeyen tür"
    )
    generator = QuestionGenerator()
    questions = generator.generate_and_resolve(d)

    # It generates default question
    assert len(questions) == 1
    assert questions[0].status == QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION
    assert questions[0].reason is not None

def test_not_applicable_resolution():
    d = Disclosure(
        disclosure_index="4",
        publish_date="2023-01-01",
        title="Test",
        content="Sözleşme görüşmeleri devam ediyor.",
        importance=DisclosureImportance.CRITICAL,
        semantic_core="Yeni iş bağlantısı/sözleşme"
    )
    generator = QuestionGenerator()
    questions = generator.generate_and_resolve(d)

    q_kapasite = next(q for q in questions if q.question == "Ek kapasite gerektiriyor mu?")
    assert q_kapasite.status == QuestionStatus.NOT_APPLICABLE
