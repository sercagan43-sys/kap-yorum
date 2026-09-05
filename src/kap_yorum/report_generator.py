from typing import Dict, List

from kap_yorum.models import (
    AnalysisResult,
    Disclosure,
    DisclosureImportance,
    FinalReport,
)


class ReportGenerator:
    """
    Synthesizes the entire 30-day window into the structured markdown user report.
    """

    def generate(self, ticker: str, disclosures: List[Disclosure], results: Dict[str, AnalysisResult]) -> FinalReport:
        report = FinalReport(ticker=ticker)

        # Stats
        report.critical_count = sum(1 for d in disclosures if d.importance == DisclosureImportance.CRITICAL)
        report.material_count = sum(1 for d in disclosures if d.importance == DisclosureImportance.MATERIAL)
        report.low_value_count = sum(1 for d in disclosures if d.importance == DisclosureImportance.LOW_ECONOMIC_VALUE)
        report.unread_count = sum(1 for d in disclosures if not d.content)

        if not disclosures:
            report.general_evaluation = "Son 30 günlük dönemde KAP açıklaması bulunamadı."
            return report

        # Synthesis
        for d in disclosures:
            if d.importance in (DisclosureImportance.CRITICAL, DisclosureImportance.MATERIAL):
                if d.semantic_core:
                    report.most_important_developments.append(f"[{d.publish_date.strftime('%Y-%m-%d')}] {d.title}: {d.semantic_core}")
                if d.real_value_point:
                    report.real_value_points.append(f"({d.title}) -> {d.real_value_point}")

            res = results.get(d.disclosure_index)
            if res:
                # Accumulate unanswered questions
                for q in res.questions:
                    if q.status == "INSUFFICIENT_PUBLIC_INFORMATION":
                        # To avoid huge duplicates in final report, we could deduplicate
                        if not any(uq.question == q.question for uq in report.unanswered_questions):
                             report.unanswered_questions.append(q)

                # Accumulate contradictions as risks
                for c in res.contradictions:
                    report.negative_risky_findings.append(c)

        # Basic synthesis logic
        if report.critical_count > 0:
            report.general_evaluation = "Şirket son 30 günde yüksek ekonomik etkiye sahip, faaliyet ölçeğini doğrudan etkileyebilecek kritik gelişmeler açıklamıştır."
            report.most_critical_conclusion = "Kapasite/Sözleşme potansiyeli finansal tabloya yansıma aşaması izlenmelidir."
        else:
            report.general_evaluation = "Son 30 gün içinde şirketin temel değerini değiştirecek kritik bir gelişme raporlanmamıştır."
            report.most_critical_conclusion = "Mevcut operasyonel durum korunmaktadır."

        return report

    def render_markdown(self, report: FinalReport) -> str:
        md = f"## [{report.ticker}] — SON 30 GÜN KAP DEĞERLENDİRMESİ\n\n"

        if report.general_evaluation == "Son 30 günlük dönemde KAP açıklaması bulunamadı.":
            md += report.general_evaluation + "\n"
            return md

        md += "### Kapsam\n"
        total = report.critical_count + report.material_count + report.low_value_count
        md += f"* incelenen açıklama: {total}\n"
        md += f"* kritik: {report.critical_count}\n"
        md += f"* anlamlı: {report.material_count}\n"
        md += f"* düşük ekonomik değer: {report.low_value_count}\n"
        if report.unread_count > 0:
            md += f"* okunamayan açıklama: {report.unread_count}\n"
        md += "\n"

        md += "### En önemli gelişmeler\n"
        for dev in report.most_important_developments:
            md += f"* {dev}\n"
        md += "\n"

        md += "### Haberlerin gerçek değer noktaları\n"
        for rvp in report.real_value_points:
            md += f"* {rvp}\n"
        md += "\n"

        md += "### Son 30 günde şirkette ne değişti?\n"
        if report.critical_count > 0:
             md += "Kapasite veya iş hacmi üzerinde doğrudan etki yaratacak bağlayıcı gelişmeler yaşanmıştır.\n"
        else:
             md += "Temel operasyonel yapıda büyük bir değişim raporlanmamıştır.\n"
        md += "\n"

        md += "### Ekonomik etki\n"
        md += "* gelir: " + (report.economic_impact.revenue or "NOT_APPLICABLE") + "\n"
        md += "* kârlılık: " + (report.economic_impact.profitability or "NOT_APPLICABLE") + "\n"
        md += "* nakit: " + (report.economic_impact.cash_flow or "NOT_APPLICABLE") + "\n"
        md += "* borç / finansman: " + (report.economic_impact.debt_financing or "NOT_APPLICABLE") + "\n"
        md += "* yatırım / kapasite: " + (report.economic_impact.investment_capacity or "NOT_APPLICABLE") + "\n"
        md += "* operasyon: " + (report.economic_impact.operation or "NOT_APPLICABLE") + "\n"
        md += "* risk: " + (report.economic_impact.risk or "NOT_APPLICABLE") + "\n\n"

        md += "### Olumlu bulgular\n"
        # Dummy fill for struct completion
        md += "* Süreç içi olumlu veri varsa buraya yansır.\n\n"

        md += "### Olumsuz / riskli bulgular\n"
        for r in report.negative_risky_findings:
             md += f"* {r}\n"
        md += "\n"

        md += "### Kamuya açık veriyle cevaplanamayan sorular\n"
        for uq in report.unanswered_questions:
             md += f"* {uq.question} -> Neden: {uq.reason}\n"
        md += "\n"

        md += "### Genel değerlendirme\n"
        md += report.general_evaluation + "\n\n"

        md += "### En kritik sonuç\n"
        md += report.most_critical_conclusion + "\n"

        return md
