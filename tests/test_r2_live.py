import pytest
from kap_yorum.resolver import CompanyResolver
from kap_yorum.models import ResolutionState

def test_live_canary_is_blocked_due_to_broken_contract():
    resolver = CompanyResolver()
    res = resolver.resolve("ASELS")
    # We expect this to fail closed because the source contract changed.
    assert res.state == ResolutionState.SOURCE_UNAVAILABLE
    assert "BLOCKED" in res.error_message
