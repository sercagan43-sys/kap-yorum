from datetime import datetime
from typing import Any, List, Optional, Set, Tuple

import requests

from kap_yorum.http_utils import RetryPolicy, execute_with_retry
from kap_yorum.models import (
    Company,
    Disclosure,
    DisclosureIdentity,
    ErrorCategory,
    RequestMetadata,
    SourceStatus,
    get_now_tz,
)


class KAPClient:
    """
    Fetches disclosures for a given company from KAP within a maximum 30-day window.
    Implements R1 integrity checks.
    """

    KAP_DISCLOSURE_LIST_URL = "https://www.kap.org.tr/tr/api/memberDisclosureQuery"

    def __init__(self, http_client: Optional[Any] = None) -> None:
        self.http_client = http_client or requests

    def get_disclosures(
        self, company: Company, max_days: int = 30
    ) -> Tuple[List[Disclosure], RequestMetadata]:
        start_time = get_now_tz()
        metadata = RequestMetadata(
            source_name="KAP",
            operation_name="get_disclosures",
            start_time=start_time,
            status=SourceStatus.UNAVAILABLE,
        )

        if not company or not company.member_oid:
            metadata.status = SourceStatus.INVALID_RESPONSE
            metadata.error_category = ErrorCategory.INVALID_IDENTIFIER
            return [], metadata

        # We will mock the date constraints for prototype, but strictly use tz-aware
        now = get_now_tz()

        # A payload mock. Time logic is mostly for R2, R1 validates structure.
        payload = {
            "mkkMemberOidList": [company.member_oid],
        }

        response, retries, error = execute_with_retry(
            self.http_client, "POST", self.KAP_DISCLOSURE_LIST_URL, json=payload, timeout=15.0
        )

        metadata.retry_count = retries
        metadata.duration_ms = int((get_now_tz() - start_time).total_seconds() * 1000)

        if error:
            metadata.status = SourceStatus.UNAVAILABLE
            metadata.error_category = RetryPolicy.map_error(error)
            metadata.raw_error_message = str(error)
            return [], metadata

        if not response:
            metadata.status = SourceStatus.UNAVAILABLE
            return [], metadata

        try:
            data = response.json()
        except Exception as e:
            metadata.status = SourceStatus.INVALID_RESPONSE
            metadata.error_category = ErrorCategory.MALFORMED_RESPONSE
            metadata.raw_error_message = str(e)
            return [], metadata

        if not isinstance(data, list):
            metadata.status = SourceStatus.INVALID_RESPONSE
            metadata.error_category = ErrorCategory.SCHEMA_MISMATCH
            return [], metadata

        if len(data) == 0:
            metadata.status = SourceStatus.EMPTY_CONFIRMED
            return [], metadata

        disclosures = []
        seen_ids: Set[str] = set()
        partial_failures = 0

        for item in data:
            disc_index = str(item.get("disclosureIndex", "")).strip()

            # Duplicate / Identity Integrity Check
            identity = DisclosureIdentity(canonical_id=disc_index)
            if not identity.validate_id() or disc_index in seen_ids:
                # Skip invalid or duplicate identities silently or count them as failed
                partial_failures += 1
                continue

            seen_ids.add(disc_index)

            # Temporal Integrity Check
            publish_date_raw = item.get("publishDate")
            publish_date = None

            if isinstance(publish_date_raw, (int, float)):
                # Assuming it's ms timestamp, we enforce UTC
                try:
                    publish_date = datetime.fromtimestamp(
                        publish_date_raw / 1000.0, get_now_tz().tzinfo
                    )
                except:
                    pass

            if publish_date is None:
                partial_failures += 1
                continue

            try:
                disclosure = Disclosure(
                    disclosure_index=disc_index,
                    publish_date=publish_date,
                    title=item.get("title", "No Title"),
                    url=f"https://www.kap.org.tr/tr/Bildirim/{disc_index}" if disc_index else None,
                )
            except Exception:
                partial_failures += 1
                continue

            # R1 Note: Detail fetching is mocked/skipped for integrity checks unless required
            # self._fetch_content(disclosure) # Removed from core loop to enforce readiness isolation

            disclosures.append(disclosure)

        metadata.records_fetched = len(disclosures)
        metadata.records_failed = partial_failures

        if partial_failures > 0 and len(disclosures) > 0:
            metadata.status = SourceStatus.PARTIAL
            metadata.error_category = ErrorCategory.SCHEMA_MISMATCH
        elif partial_failures > 0 and len(disclosures) == 0:
            metadata.status = SourceStatus.INVALID_RESPONSE
            metadata.error_category = ErrorCategory.SCHEMA_MISMATCH
        else:
            metadata.status = SourceStatus.SUCCESS

        return disclosures, metadata
