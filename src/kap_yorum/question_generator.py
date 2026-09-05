from typing import List, Dict
from kap_yorum.models import Disclosure, DisclosureImportance, EconomicQuestion, QuestionStatus

class QuestionGenerator:
    """
    Generates economic questions based on semantic core and attempts to resolve them.
    Every question must be closed with a valid status.
    """

    def generate_and_resolve(self, disclosure: Disclosure) -> List[EconomicQuestion]:
        if disclosure.importance == DisclosureImportance.LOW_ECONOMIC_VALUE:
            return []

        questions = []
        core = disclosure.semantic_core or ""

        # 1. Generate questions based on core type
        if "sözleşme" in core:
            questions.append(EconomicQuestion(question="Kesinleşmiş mi?", status=QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION))
            questions.append(EconomicQuestion(question="Tutarı ne?", status=QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION))
            questions.append(EconomicQuestion(question="Şirket için önemli büyüklükte mi?", status=QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION))
            questions.append(EconomicQuestion(question="Kârlılık hakkında yeterli bilgi var mı?", status=QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION))
            questions.append(EconomicQuestion(question="Ek kapasite gerektiriyor mu?", status=QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION))

        elif "yatırım" in core:
            questions.append(EconomicQuestion(question="Yatırımın toplam tutarı ne kadar?", status=QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION))
            questions.append(EconomicQuestion(question="Finansmanı nasıl sağlanacak (özkaynak/borç)?", status=QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION))
            questions.append(EconomicQuestion(question="Ne zaman devreye alınacak?", status=QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION))
            questions.append(EconomicQuestion(question="Beklenen ciro/kâr katkısı nedir?", status=QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION))

        elif "finansal" in core:
            questions.append(EconomicQuestion(question="Ciro/kâr büyümesi enflasyonun üzerinde mi?", status=QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION))
            questions.append(EconomicQuestion(question="Borçluluk oranı ne durumda?", status=QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION))

        else:
             questions.append(EconomicQuestion(question="Şirket faaliyetlerine doğrudan ekonomik etkisi var mı?", status=QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION))

        # 2. Resolve questions based on available facts (heuristic mockup)
        facts_text = " ".join(disclosure.verified_facts).lower() if disclosure.verified_facts else ""
        content_text = disclosure.content.lower() if disclosure.content else ""

        for q in questions:
            if q.question == "Kesinleşmiş mi?":
                if "imzalandı" in facts_text or "imzalanmıştır" in content_text:
                    q.status = QuestionStatus.ANSWERED
                    q.answer = "Evet, sözleşme imzalanmıştır."
                else:
                    q.status = QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION
                    q.reason = "Metinde imza aşamasına gelindiğine dair kesin bilgi yok, görüşme aşamasında olabilir."

            elif q.question == "Tutarı ne?":
                if "tutar" in facts_text or "milyon" in facts_text or "milyar" in facts_text:
                    q.status = QuestionStatus.ANSWERED
                    q.answer = "Tutar bilgisi metinde belirtilmiştir."
                else:
                    q.status = QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION
                    q.reason = "Sözleşme tutarı açıklanmamıştır."

            elif q.question == "Kârlılık hakkında yeterli bilgi var mı?":
                q.status = QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION
                q.reason = "Şirket ticari sır olduğu gerekçesiyle veya teamülen kâr marjını açıklamamıştır. Net kâr etkisi güvenilir biçimde hesaplanamaz."

            elif q.question == "Ek kapasite gerektiriyor mu?":
                 if "kapasite" in content_text or "yatırım" in content_text:
                     q.status = QuestionStatus.ANSWERED
                     q.answer = "Metinde kapasite artışına işaret edilmektedir."
                 else:
                     q.status = QuestionStatus.NOT_APPLICABLE

            elif q.question == "Şirket için önemli büyüklükte mi?":
                 # Fallback to INSUFFICIENT with a reason if not answered
                 q.status = QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION
                 q.reason = "Tutar belirtilse dahi önceki yılın cirosu bağlamı verilmediği için oransal büyüklük teyit edilememiştir."

            else:
                 # Default closure if not specifically handled
                 if q.status == QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION and not q.reason:
                     q.reason = "Kamuya açıklanan metinde bu soruyu yanıtlayacak detay yer almamaktadır."

        # Safety check: No question should be left open (without status or INSUFFICIENT without reason)
        for q in questions:
            if q.status == QuestionStatus.INSUFFICIENT_PUBLIC_INFORMATION and not q.reason:
                 q.reason = "[SİSTEM GÜVENLİK KAPANIŞI] Metinde yeterli bilgi bulunamadı."

        return questions
