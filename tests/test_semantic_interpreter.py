from datetime import datetime

from kap_yorum.models import Disclosure, DisclosureImportance
from kap_yorum.semantic_interpreter import SemanticInterpreter


def test_semantic_interpreter_contract():
    d = Disclosure(
        disclosure_index="1",
        publish_date=datetime.now(),
        title="Yeni İş İlişkisi",
        content="Yeni bir sözleşme imzalanmıştır."
    )
    interpreter = SemanticInterpreter()
    interpreter.interpret(d)

    assert d.semantic_core == "Yeni iş bağlantısı/sözleşme"
    assert "Tutarın şirketin mevcut faaliyet ölçeğine göre önemi" in d.real_value_point
    assert d.importance == DisclosureImportance.CRITICAL

def test_semantic_interpreter_investment():
    d = Disclosure(
        disclosure_index="2",
        publish_date=datetime.now(),
        title="Yatırım",
        content="Yeni bir fabrika yatırımı kararı alınmıştır."
    )
    interpreter = SemanticInterpreter()
    interpreter.interpret(d)

    assert d.semantic_core == "Kapasite artışı / yeni yatırım"
    assert "ek gelir potansiyeli ve finansman yükü" in d.real_value_point
    assert d.importance == DisclosureImportance.CRITICAL

def test_semantic_interpreter_management():
    d = Disclosure(
        disclosure_index="3",
        publish_date=datetime.now(),
        title="Atama",
        content="Yönetim kuruluna atama yapıldı."
    )
    interpreter = SemanticInterpreter()
    interpreter.interpret(d)

    assert d.semantic_core == "Yönetim/Organizasyon değişikliği"
    assert d.importance == DisclosureImportance.MATERIAL

def test_semantic_interpreter_low_value():
    d = Disclosure(
        disclosure_index="4",
        publish_date=datetime.now(),
        title="Olağan Genel Kurul Çağrısı",
        content="Toplantı tarihi belirlenmiştir."
    )
    interpreter = SemanticInterpreter()
    interpreter.interpret(d)

    assert d.semantic_core == "Rutin açıklama"
    assert d.importance == DisclosureImportance.LOW_ECONOMIC_VALUE
    assert "bulunmuyor" in d.real_value_point

def test_semantic_interpreter_empty_content():
    d = Disclosure(
        disclosure_index="5",
        publish_date=datetime.now(),
        title="Boş",
        content=None
    )
    interpreter = SemanticInterpreter()
    interpreter.interpret(d)
    assert d.importance == DisclosureImportance.LOW_ECONOMIC_VALUE
