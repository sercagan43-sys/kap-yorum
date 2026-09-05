from typing import Dict, List

from kap_yorum.models import AnalysisResult, Disclosure, DisclosureImportance


class EventRelationshipAnalyzer:
    """
    Analyzes relationships between disclosures within the 30-day window.
    Handles continuations, corrections, and contradictions.
    """

    def process_relationships(self, disclosures: List[Disclosure], analysis_results: Dict[str, AnalysisResult]) -> None:
        """
        In-place modification of analysis_results to add relationships and contradictions,
        and update disclosure objects for corrections.
        """

        # Sort disclosures by date (oldest first) to apply chronologically
        sorted_discs = sorted(disclosures, key=lambda x: x.publish_date)

        # Basic loop protection mapping
        processed = set()

        for current in sorted_discs:
            if current.disclosure_index in processed:
                continue

            current_res = analysis_results.get(current.disclosure_index)
            if not current_res:
                continue

            # Check for corrections
            if current.semantic_core == "Önceki açıklamanın düzeltilmesi" or current.is_correction:
                # Find the most likely target (in a real system, KAP data explicitly links `relatedDisclosureOid`)
                # Here we simulate finding the latest similar event
                target = self._find_correction_target(current, sorted_discs)
                if target:
                     current_res.related_disclosures.append(f"Düzeltme hedefi: {target.disclosure_index}")
                     if target.disclosure_index in analysis_results:
                         analysis_results[target.disclosure_index].contradictions.append(
                             f"DİKKAT: Bu açıklama {current.disclosure_index} numaralı açıklama ile düzeltilmiştir. Geçersiz bilgi içeriyor olabilir."
                         )
                         target.importance = DisclosureImportance.LOW_ECONOMIC_VALUE # Demote old

            # Check for continuations (e.g. same contract negotiation -> signed)
            if current.semantic_core == "Yeni iş bağlantısı/sözleşme":
                previous = self._find_previous_similar(current, sorted_discs, "Yeni iş bağlantısı/sözleşme")
                if previous:
                    current_res.related_disclosures.append(f"Devam haberi niteliğinde: {previous.disclosure_index}")
                    if previous.disclosure_index in analysis_results:
                        analysis_results[previous.disclosure_index].related_disclosures.append(f"Süreç sonucu: {current.disclosure_index}")

            # Check for contradictions/risks across the window
            if current.semantic_core == "Kapasite artışı / yeni yatırım":
                # If there's an investment, is there also high new borrowing?
                borrowings = [d for d in sorted_discs if d.semantic_core == "Finansman / borçlanma"]
                if borrowings:
                    current_res.contradictions.append(
                        "Risk Faktörü: Aynı dönemde yatırım yaparken yeni borçlanma/finansman ihtiyacı gözlemlenmiştir. "
                        "Yatırımın finansman maliyeti nakit akışını etkileyebilir."
                    )

            processed.add(current.disclosure_index)

    def _find_correction_target(self, current: Disclosure, discs: List[Disclosure]) -> Disclosure | None:
        # Heuristic: find immediately preceding disclosure of same title/type or by title match
        # Simplified for prototype
        for d in reversed(discs):
             if d.publish_date < current.publish_date and d.disclosure_index != current.disclosure_index:
                  return d
        return None

    def _find_previous_similar(self, current: Disclosure, discs: List[Disclosure], core_type: str) -> Disclosure | None:
         for d in reversed(discs):
             if d.publish_date < current.publish_date and d.semantic_core == core_type:
                  return d
         return None
