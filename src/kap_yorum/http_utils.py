import time
from typing import Any, Optional, Tuple

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

from kap_yorum.models import ErrorCategory


class RetryPolicy:
    """Strict retry policy for HTTP requests."""

    MAX_RETRIES = 2
    TIMEOUT_SEC = 10.0

    @staticmethod
    def is_retryable(error: Exception) -> bool:
        if isinstance(error, Timeout):
            return True
        if isinstance(error, ConnectionError):
            return True
        if isinstance(error, RequestException):
            # E.g. 500, 502, 503, 504 are retryable
            if error.response is not None:
                if error.response.status_code in (500, 502, 503, 504):
                    return True
        return False

    @staticmethod
    def map_error(error: Exception) -> ErrorCategory:
        if isinstance(error, Timeout):
            return ErrorCategory.TIMEOUT
        if isinstance(error, ConnectionError):
            return ErrorCategory.CONNECTION_FAILURE
        if isinstance(error, RequestException):
            if error.response is not None:
                if error.response.status_code == 429:
                    return ErrorCategory.RATE_LIMIT
                if error.response.status_code in (401, 403):
                    return ErrorCategory.AUTH_ERROR
            return ErrorCategory.HTTP_ERROR
        return ErrorCategory.NONE

def execute_with_retry(http_client: Any, method: str, url: str, **kwargs: Any) -> Tuple[requests.Response, int, Optional[Exception]]:
    """
    Executes an HTTP request with a strict retry and timeout policy.
    Returns: (Response object (if any), retry_count, Exception (if failed))
    """
    retries = 0
    last_exception = None

    if "timeout" not in kwargs:
        kwargs["timeout"] = RetryPolicy.TIMEOUT_SEC

    while retries <= RetryPolicy.MAX_RETRIES:
        try:
            if method.upper() == "GET":
                response = http_client.get(url, **kwargs)
            elif method.upper() == "POST":
                response = http_client.post(url, **kwargs)
            else:
                raise ValueError(f"Unsupported method {method}")

            response.raise_for_status()
            return response, retries, None

        except Exception as e:
            last_exception = e
            if RetryPolicy.is_retryable(e):
                retries += 1
                if retries <= RetryPolicy.MAX_RETRIES:
                    # Deterministic backoff without infinite loop
                    time.sleep(0.5 * retries)
                continue
            else:
                break

    return None, retries, last_exception # type: ignore
