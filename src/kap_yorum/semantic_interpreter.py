from kap_yorum.models import Disclosure, DisclosureImportance


class SemanticInterpreter:
    """
    Extracts the 'semantic core' (What is this really about?) and
    'real value point' (Where is the true economic value created?)
    from a disclosure.
    """

    def interpret(self, disclosure: Disclosure) -> None:
        """
        Populates semantic_core, real_value_point, and importance.
        """
        if not disclosure.content and not disclosure.verified_facts:
            disclosure.importance = DisclosureImportance.LOW_ECONOMIC_VALUE
            return

        text = disclosure.content.lower() if disclosure.content else ""

        if "sözleşme" in text or "iş ilişkisi" in text:
            disclosure.semantic_core = "Yeni iş bağlantısı/sözleşme"
            disclosure.real_value_point = (
                "Tutarın şirketin mevcut faaliyet ölçeğine göre önemi ve kesinleşme durumu"
            )
            disclosure.importance = DisclosureImportance.CRITICAL

        elif "yatırım" in text or "kapasite" in text:
            disclosure.semantic_core = "Kapasite artışı / yeni yatırım"
            disclosure.real_value_point = (
                "Yatırımın yaratacağı ek gelir potansiyeli ve finansman yükü"
            )
            disclosure.importance = DisclosureImportance.CRITICAL

        elif "finansal" in text or "bilanço" in text or "gelir tablosu" in text:
            disclosure.semantic_core = "Dönem finansal sonuçları"
            disclosure.real_value_point = (
                "Net kar, ciro büyümesi ve operasyonel nakit akışı performansı"
            )
            disclosure.importance = DisclosureImportance.CRITICAL

        elif "atama" in text or "istifa" in text:
            disclosure.semantic_core = "Yönetim/Organizasyon değişikliği"
            disclosure.real_value_point = "Stratejik yönelimdeki olası değişimler"
            disclosure.importance = DisclosureImportance.MATERIAL

        elif "düzeltme" in text:
            disclosure.semantic_core = "Önceki açıklamanın düzeltilmesi"
            disclosure.real_value_point = (
                "Eski bilginin geçersiz kalması ve yeni etkinin hesaplanması"
            )
            disclosure.importance = DisclosureImportance.MATERIAL

        elif "kredi" in text or "borçlanma" in text or "finansman" in text:
            disclosure.semantic_core = "Finansman / borçlanma"
            disclosure.real_value_point = "Şirketin finansman maliyeti ve borç ödeme kapasitesi"
            disclosure.importance = DisclosureImportance.MATERIAL

        else:
            disclosure.semantic_core = "Rutin açıklama"
            disclosure.real_value_point = "Spesifik bir ekonomik değer noktası bulunmuyor"
            disclosure.importance = DisclosureImportance.LOW_ECONOMIC_VALUE
