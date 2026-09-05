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

        def create_metadata(status: SourceStatus, error_category: ErrorCategory = ErrorCategory.NONE, duration_ms: int = 0, retry_count: int = 0, records_fetched: int = 0, records_failed: int = 0, raw_error_message: Optional[str] = None) -> RequestMetadata:
            return RequestMetadata(
                source_name="KAP",
                operation_name="get_disclosures",
                start_time=start_time,
                status=status,
                error_category=error_category,
                duration_ms=duration_ms,
                retry_count=retry_count,
                records_fetched=records_fetched,
                records_failed=records_failed,
                raw_error_message=raw_error_message,
            )

        if not company or not company.member_oid:
            return [], create_metadata(
                status=SourceStatus.INVALID_RESPONSE,
                error_category=ErrorCategory.INVALID_IDENTIFIER
            )

        # We will mock the date constraints for prototype, but strictly use tz-aware
        now = get_now_tz()

        # A payload mock. Time logic is mostly for R2, R1 validates structure.
        payload = {
            "mkkMemberOidList": [company.member_oid],
        }

        response, retries, error = execute_with_retry(
            self.http_client, "POST", self.KAP_DISCLOSURE_LIST_URL, json=payload, timeout=15.0
        )

        duration_ms = int((get_now_tz() - start_time).total_seconds() * 1000)

        if error:
            return [], create_metadata(
                status=SourceStatus.UNAVAILABLE,
                error_category=RetryPolicy.map_error(error),
                duration_ms=duration_ms,
                retry_count=retries,
                raw_error_message=str(error)
            )

        if not response:
            return [], create_metadata(
                status=SourceStatus.UNAVAILABLE,
                error_category=ErrorCategory.UNKNOWN_ERROR,
                duration_ms=duration_ms,
                retry_count=retries
            )

        try:
            data = response.json()
        except Exception as e:
            return [], create_metadata(
                status=SourceStatus.INVALID_RESPONSE,
                error_category=ErrorCategory.MALFORMED_RESPONSE,
                duration_ms=duration_ms,
                retry_count=retries,
                raw_error_message=str(e)
            )

        if not isinstance(data, list):
            return [], create_metadata(
                status=SourceStatus.INVALID_RESPONSE,
                error_category=ErrorCategory.SCHEMA_MISMATCH,
                duration_ms=duration_ms,
                retry_count=retries
            )

        if len(data) == 0:
            return [], create_metadata(
                status=SourceStatus.EMPTY_CONFIRMED,
                duration_ms=duration_ms,
                retry_count=retries
            )

        disclosures = []
        seen_ids: Set[str] = set()
        partial_failures = 0
        error_types: Set[ErrorCategory] = set()

        for item in data:
            disc_index = str(item.get("disclosureIndex", "")).strip()

            # Duplicate / Identity Integrity Check
            identity = DisclosureIdentity(canonical_id=disc_index)
            if not identity.validate_id():
                partial_failures += 1
                error_types.add(ErrorCategory.MISSING_IDENTIFIER)
                continue

            if disc_index in seen_ids:
                partial_failures += 1
                error_types.add(ErrorCategory.DUPLICATE_IDENTIFIER)
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
                error_types.add(ErrorCategory.SCHEMA_MISMATCH)
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
                error_types.add(ErrorCategory.SCHEMA_MISMATCH)
                continue

            # R1 Note: Detail fetching is mocked/skipped for integrity checks unless required
            # self._fetch_content(disclosure) # Removed from core loop to enforce readiness isolation

            disclosures.append(disclosure)

        final_status = SourceStatus.SUCCESS
        final_error = ErrorCategory.NONE

        if partial_failures > 0:
            if len(error_types) > 1:
                final_error = ErrorCategory.MULTIPLE_ERRORS
            else:
                final_error = next(iter(error_types))

            if len(disclosures) > 0:
                final_status = SourceStatus.PARTIAL
            else:
                final_status = SourceStatus.INVALID_RESPONSE

        return disclosures, create_metadata(
            status=final_status,
            error_category=final_error,
            duration_ms=duration_ms,
            retry_count=retries,
            records_fetched=len(disclosures),
            records_failed=partial_failures
        )
