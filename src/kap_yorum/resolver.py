from typing import Any, Optional

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from kap_yorum.models import (
    Company,
    CompanyState,
    EntityType,
    ResolutionState,
    TickerResolutionResult,
)


class CompanyResolver:
    """
    Validates BIST tickers and resolves them to company details using KAP API.
    """

    KAP_AUTOCOMPLETE_URL = "https://www.kap.org.tr/tr/api/autocomplete"

    def __init__(self, http_client: Optional[Any] = None) -> None:
        self.http_client = http_client or requests

    def resolve(self, ticker: str) -> TickerResolutionResult:
        if not ticker or not isinstance(ticker, str):
            return TickerResolutionResult(
                state=ResolutionState.NOT_FOUND,
                error_message="Invalid ticker format"
            )

        ticker = ticker.strip().upper()
        if not ticker:
            return TickerResolutionResult(
                state=ResolutionState.NOT_FOUND,
                error_message="Empty ticker"
            )

        try:
            response = self.http_client.get(self.KAP_AUTOCOMPLETE_URL, timeout=10)

            # Immediately block if external contract is broken
            if response.status_code == 404:
                return TickerResolutionResult(
                    state=ResolutionState.SOURCE_UNAVAILABLE,
                    error_message="BLOCKED: KAP API autocomplete endpoint returned 404, contract changed."
                )

            response.raise_for_status()

            try:
                data = response.json()
            except Exception as e:
                return TickerResolutionResult(
                    state=ResolutionState.INVALID_RESPONSE,
                    error_message=f"JSON parsing failed: {e}"
                )

            if not isinstance(data, list):
                return TickerResolutionResult(
                    state=ResolutionState.INVALID_RESPONSE,
                    error_message="Expected list from KAP autocomplete."
                )

            found_companies = []
            for item in data:
                if "mkkKodu" in item and item["mkkKodu"].strip().upper() == ticker:
                    found_companies.append(item)

            if not found_companies:
                return TickerResolutionResult(
                    state=ResolutionState.NOT_FOUND,
                    error_message=f"Ticker {ticker} not found in universe."
                )

            if len(found_companies) > 1:
                return TickerResolutionResult(
                    state=ResolutionState.IDENTITY_CONFLICT,
                    error_message=f"Multiple identities found for ticker {ticker}."
                )

            item = found_companies[0]
            # Map known active/type constraints if they existed, else UNKNOWN for now until real contract reveals it.
            return TickerResolutionResult(
                state=ResolutionState.RESOLVED,
                company=Company(
                    ticker=ticker,
                    name=item.get("unvan", ticker),
                    member_oid=item.get("memberOid"),
                    canonical_identity=item.get("memberOid"),
                    entity_type=EntityType.UNKNOWN,
                    state=CompanyState.UNKNOWN,
                    source_provenance="KAP_PUBLIC"
                )
            )

        except (Timeout, ConnectionError) as e:
            return TickerResolutionResult(
                state=ResolutionState.SOURCE_UNAVAILABLE,
                error_message=f"Network error: {str(e)}"
            )
        except RequestException as e:
             resp = getattr(e, 'response', None)
             if resp is not None and hasattr(resp, 'status_code') and resp.status_code >= 500:
                 return TickerResolutionResult(
                    state=ResolutionState.SOURCE_UNAVAILABLE,
                    error_message=f"Server error: {resp.status_code}"
                )
             return TickerResolutionResult(
                state=ResolutionState.SOURCE_UNAVAILABLE,
                error_message=f"Request error: {str(e)}"
            )
        except Exception as e:
            return TickerResolutionResult(
                state=ResolutionState.INVALID_RESPONSE,
                error_message=f"Unknown error during resolution: {str(e)}"
            )
