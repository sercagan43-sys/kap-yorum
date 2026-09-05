from typing import Optional
from kap_yorum.resolver import CompanyResolver
from kap_yorum.kap_client import KAPClient
from kap_yorum.fact_extractor import FactExtractor
from kap_yorum.semantic_interpreter import SemanticInterpreter
from kap_yorum.question_generator import QuestionGenerator
from kap_yorum.economic_analyzer import EconomicAnalyzer
from kap_yorum.relationship_analyzer import EventRelationshipAnalyzer
from kap_yorum.report_generator import ReportGenerator

class KAPYorumEngine:
    """
    Main orchestration engine ensuring strict adherence to flow and loop prevention.
    """
    def __init__(self, http_client=None):
        self.resolver = CompanyResolver(http_client)
        self.kap_client = KAPClient(http_client)
        self.fact_extractor = FactExtractor()
        self.semantic_interpreter = SemanticInterpreter()
        self.question_generator = QuestionGenerator()
        self.economic_analyzer = EconomicAnalyzer()
        self.relationship_analyzer = EventRelationshipAnalyzer()
        self.report_generator = ReportGenerator()

    def run(self, ticker: str) -> str:
        # 1. Ticker Validation & Company Resolution
        company = self.resolver.resolve(ticker)
        if not company:
            return f"Hata: '{ticker}' kodlu şirket bulunamadı veya geçerli bir BIST kodu değil."

        # 2. Maximum 30-day disclosure retrieval & content (Client handles network faults)
        try:
            disclosures = self.kap_client.get_disclosures(company, max_days=30)
        except ConnectionError as e:
            return f"Erişim Hatası: {str(e)}"

        if not disclosures:
             # Fast-track empty report
             report = self.report_generator.generate(company.ticker, [], {})
             return self.report_generator.render_markdown(report)

        analysis_results = {}
        processed_indexes = set() # Loop prevention at orchestrator level

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
        # We also need to map the combined economic impact to the final report
        # Here we just take the last CRITICAL or MATERIAL impact for the prototype

        report = self.report_generator.generate(company.ticker, disclosures, analysis_results)

        # Fill overall economic impact if available
        for d in reversed(disclosures):
             if d.disclosure_index in analysis_results and d.importance in ["CRITICAL", "MATERIAL"]:
                  res = analysis_results[d.disclosure_index]
                  report.economic_impact = res.impact
                  break

        return self.report_generator.render_markdown(report)
