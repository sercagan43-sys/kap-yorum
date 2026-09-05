from kap_yorum.models import Disclosure


class FactExtractor:
    """
    Extracts verified facts from disclosure content, explicitly separating
    them from inferences or future projections.
    """

    def extract_facts(self, disclosure: Disclosure) -> None:
        """
        Populates the disclosure.verified_facts list.
        In a real AI implementation, this would use an LLM or NLP.
        For this prototype structure, we will use basic heuristic extraction
        and demonstrate the separation concept.
        """
        if not disclosure.content:
            return

        facts = []
        text = disclosure.content.lower()

        # Prototype logic: simulate fact extraction
        if "sözleşme imzalanmıştır" in text or "contract signed" in text:
            facts.append("Sözleşme imzalandı.")

        if "milyon" in text or "milyar" in text:
            # We would extract the exact number
            facts.append("Tutar/büyüklük bilgisi mevcut.")

        if "kar edecek" in text or "beklenmektedir" in text:
            # Explicitly exclude inferences/expectations from facts
            pass

        # If no explicit facts found via rules, we use a fallback for testing
        if not facts and disclosure.content.strip():
            facts.append(f"Açıklama yapıldı: {disclosure.title}")

        disclosure.verified_facts = facts
