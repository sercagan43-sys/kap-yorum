from typing import Any, Optional

from kap_yorum.economic_analyzer import EconomicAnalyzer
from kap_yorum.fact_extractor import FactExtractor
from kap_yorum.kap_client import KAPClient
from kap_yorum.models import SourceStatus, SystemReadiness
from kap_yorum.question_generator import QuestionGenerator
from kap_yorum.relationship_analyzer import EventRelationshipAnalyzer
from kap_yorum.report_generator import ReportGenerator
from kap_yorum.resolver import CompanyResolver
from kap_yorum.semantic_interpreter import SemanticInterpreter


class KAPYorumEngine:
    """
    Main orchestration engine ensuring strict adherence to flow, loop prevention,
    and R1 Capability / Readiness boundaries.
    """

    def __init__(self, http_client: Optional[Any] = None) -> None:
        self.resolver = CompanyResolver(http_client)
        self.kap_client = KAPClient(http_client)
        self.fact_extractor = FactExtractor()
        self.semantic_interpreter = SemanticInterpreter()
        self.question_generator = QuestionGenerator()
        self.economic_analyzer = EconomicAnalyzer()
        self.relationship_analyzer = EventRelationshipAnalyzer()
        self.report_generator = ReportGenerator()

        # By default, R1 dictates that none of these capabilities are fully READY
        # until the real source integration in R2/R3 is built and verified.
        self._readiness = SystemReadiness()

    @property
    def _is_production_ready(self) -> bool:
        # In R1, we strictly return False to seal the state machine for production.
        # This completely ignores external mutation of self._readiness.
        # Test frameworks can override this property specifically, rather than mutating state.
        return False

    def run(self, ticker: str) -> str:
        # FAIL-CLOSED R1 Readiness Gate
        if not self._is_production_ready:
            return (
                "[SİSTEM GÜVENLİK KAPANIŞI] Kaynak ve Veri Bütünlüğü Altyapısı (R1) "
                "gerçek kaynak katmanı için henüz hazır değil (SOURCE_LAYER_NOT_VALIDATED). "
                "Prototype veya sahte analiz üretimi engellendi."
            )

        # 1. Ticker Validation & Company Resolution
        company = self.resolver.resolve(ticker)
        if not company:
            return f"Hata: '{ticker}' kodlu şirket bulunamadı veya geçerli bir BIST kodu değil."

        # 2. Maximum 30-day disclosure retrieval & content (Client handles network faults via typed metadata)
        disclosures, metadata = self.kap_client.get_disclosures(company, max_days=30)

        if metadata.status == SourceStatus.UNAVAILABLE:
            return (
                f"Erişim Hatası: KAP'a erişim sağlanamadı. (Hata Sınıfı: {metadata.error_category})"
            )

        if metadata.status == SourceStatus.INVALID_RESPONSE:
            return f"Kaynak Hatası: KAP'tan geçersiz veri formatı alındı. (Hata Sınıfı: {metadata.error_category})"

        if metadata.status == SourceStatus.EMPTY_CONFIRMED or not disclosures:
            # Fast-track empty report (Confirmed empty)
            report = self.report_generator.generate(company.ticker, [], {})
            return self.report_generator.render_markdown(report)

        analysis_results = {}
        processed_indexes = set()  # Loop prevention at orchestrator level

        # 3. to 6. Iterate and analyze independently (no cross-talk yet)
        for d in disclosures:
            if d.disclosure_index in processed_indexes:
                continue
            processed_indexes.add(d.disclosure_index)

            # Content normalization / Fact extraction
            self.fact_extractor.extract_facts(d)

            # Semantic interpretation
            self.semantic_interpreter.interpret(d)

            # Question generation & controlled resolution
            questions = self.question_generator.generate_and_resolve(d)

            # Economic value analysis
            res = self.economic_analyzer.analyze(d, questions)
            analysis_results[d.disclosure_index] = res

        # 7. Event relationship analysis (continuations, contradictions, corrections)
        self.relationship_analyzer.process_relationships(disclosures, analysis_results)

        # 8. Monthly company synthesis & User report
        report = self.report_generator.generate(company.ticker, disclosures, analysis_results)

        # Fill overall economic impact if available
        for d in reversed(disclosures):
            if d.disclosure_index in analysis_results and d.importance in ["CRITICAL", "MATERIAL"]:
                res = analysis_results[d.disclosure_index]
                report.economic_impact = res.impact
                break

        return self.report_generator.render_markdown(report)
