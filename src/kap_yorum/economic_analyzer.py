from typing import List

from kap_yorum.models import (
    AnalysisResult,
    Disclosure,
    DisclosureImportance,
    EconomicQuestion,
)


class EconomicAnalyzer:
    """
    Analyzes the economic impact of a disclosure across specific domains.
    Returns an AnalysisResult.
    """

    def analyze(self, disclosure: Disclosure, questions: List[EconomicQuestion]) -> AnalysisResult:
        result = AnalysisResult(
            disclosure_id=disclosure.disclosure_index,
            questions=questions
        )

        if disclosure.importance == DisclosureImportance.LOW_ECONOMIC_VALUE:
            # Explicitly state NO_ECONOMIC_VALUE logic from rules
            return result

        core = disclosure.semantic_core or ""
        text = (disclosure.content or "").lower()

        # Populate impact based on core and content
        if "sözleşme" in core:
            result.impact.revenue = "Yeni sözleşme tutarı oranında gelir artışı potansiyeli yaratır."
            result.impact.profitability = "Sözleşme marjı açıklanmadığı için kesin kârlılık etkisi bilinememektedir."
            result.impact.cash_flow = "NOT_APPLICABLE - Ödeme takvimi belli değil."
            result.impact.debt_financing = "NOT_APPLICABLE"
            result.impact.investment_capacity = "NOT_APPLICABLE"
            result.impact.operation = "İş hacminde artış."
            result.impact.risk = "Uygulama veya tahsilat riski olağan ticari döngü içindedir."

        elif "yatırım" in core:
            result.impact.revenue = "Orta/uzun vadede kapasite artışına bağlı gelir potansiyeli."
            result.impact.profitability = "Amortisman yükü kısa vadede kârlılığı baskılayabilir."
            result.impact.cash_flow = "Yatırım döneminde nakit çıkışı yaşanacaktır."
            result.impact.debt_financing = "Finansman ihtiyacı yeni borçlanma gerektirebilir."
            result.impact.investment_capacity = "Mevcut yatırım kararı."
            result.impact.operation = "Kapasite artışı sağlanacak."
            result.impact.risk = "Proje takvimi sapma riski ve finansman maliyeti artış riski."

        elif "finansal" in core:
            result.impact.revenue = "Gerçekleşmiş gelir tablosu verisi."
            result.impact.profitability = "Gerçekleşmiş kârlılık verisi."
            result.impact.cash_flow = "Gerçekleşmiş nakit akış verisi."
            result.impact.debt_financing = "Bilanço borçluluk durumu."

        else:
            # Set NOT_APPLICABLE for irrelevant domains to avoid forced interpretations
            result.impact.revenue = "NOT_APPLICABLE"
            result.impact.profitability = "NOT_APPLICABLE"
            result.impact.cash_flow = "NOT_APPLICABLE"
            result.impact.debt_financing = "NOT_APPLICABLE"
            result.impact.investment_capacity = "NOT_APPLICABLE"
            result.impact.operation = "NOT_APPLICABLE"
            result.impact.risk = "NOT_APPLICABLE"

            if "atama" in core:
                 result.impact.operation = "Yönetimsel değişiklik."

        return result
