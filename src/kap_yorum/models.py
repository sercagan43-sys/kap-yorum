from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class SourceStatus(str, Enum):
    SUCCESS = "SUCCESS"
    EMPTY_CONFIRMED = "EMPTY_CONFIRMED"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"
    INVALID_RESPONSE = "INVALID_RESPONSE"

class ErrorCategory(str, Enum):
    TIMEOUT = "TIMEOUT"
    CONNECTION_FAILURE = "CONNECTION_FAILURE"
    HTTP_ERROR = "HTTP_ERROR"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    AUTH_ERROR = "AUTH_ERROR"
    RATE_LIMIT = "RATE_LIMIT"
    PARTIAL_CHILD_FAILURE = "PARTIAL_CHILD_FAILURE"
    INVALID_IDENTIFIER = "INVALID_IDENTIFIER"
    NONE = "NONE"

class RequestMetadata(BaseModel):
    source_name: str
    operation_name: str
    start_time: datetime
    duration_ms: int = 0
    status: SourceStatus
    records_fetched: int = 0
    records_failed: int = 0
    error_category: ErrorCategory = ErrorCategory.NONE
    retry_count: int = 0
    raw_error_message: Optional[str] = None

class CapabilityStatus(str, Enum):
    READY = "READY"
    NOT_READY = "NOT_READY"

class SystemReadiness(BaseModel):
    ticker_resolution: CapabilityStatus = CapabilityStatus.NOT_READY
    disclosure_listing: CapabilityStatus = CapabilityStatus.NOT_READY
    disclosure_detail: CapabilityStatus = CapabilityStatus.NOT_READY
    structured_fields: CapabilityStatus = CapabilityStatus.NOT_READY
    attachments: CapabilityStatus = CapabilityStatus.NOT_READY
    financial_context: CapabilityStatus = CapabilityStatus.NOT_READY
    semantic_analysis: CapabilityStatus = CapabilityStatus.NOT_READY
    economic_analysis: CapabilityStatus = CapabilityStatus.NOT_READY

    @property
    def source_layer_validated(self) -> bool:
        return (
            self.ticker_resolution == CapabilityStatus.READY and
            self.disclosure_listing == CapabilityStatus.READY and
            self.disclosure_detail == CapabilityStatus.READY
        )

# Timezone-aware date generator
def get_now_tz() -> datetime:
    return datetime.now(timezone.utc)

# Identity contract
class DisclosureIdentity(BaseModel):
    canonical_id: str
    source_system: str = "KAP"

    def validate_id(self) -> bool:
        return bool(self.canonical_id and self.canonical_id.strip())

class DisclosureIdentityError(Exception):
    pass

# We redefine or augment the previous models to ensure timezone awareness
class QuestionStatus(str, Enum):
    ANSWERED = "ANSWERED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NO_ECONOMIC_VALUE = "NO_ECONOMIC_VALUE"
    INSUFFICIENT_PUBLIC_INFORMATION = "INSUFFICIENT_PUBLIC_INFORMATION"

class DisclosureImportance(str, Enum):
    CRITICAL = "CRITICAL"
    MATERIAL = "MATERIAL"
    LOW_ECONOMIC_VALUE = "LOW_ECONOMIC_VALUE"

class Company(BaseModel):
    ticker: str
    name: str
    member_oid: Optional[str] = None

class Disclosure(BaseModel):
    disclosure_index: str
    publish_date: datetime # Must be tz-aware
    title: str
    content: Optional[str] = None
    url: Optional[str] = None
    is_correction: bool = False

    importance: DisclosureImportance = DisclosureImportance.LOW_ECONOMIC_VALUE
    verified_facts: List[str] = Field(default_factory=list)
    semantic_core: Optional[str] = None
    real_value_point: Optional[str] = None

class EconomicQuestion(BaseModel):
    question: str
    status: QuestionStatus
    answer: Optional[str] = None
    reason: Optional[str] = None

class EconomicImpact(BaseModel):
    revenue: Optional[str] = None
    profitability: Optional[str] = None
    cash_flow: Optional[str] = None
    debt_financing: Optional[str] = None
    investment_capacity: Optional[str] = None
    operation: Optional[str] = None
    risk: Optional[str] = None

class AnalysisResult(BaseModel):
    disclosure_id: str
    questions: List[EconomicQuestion] = Field(default_factory=list)
    impact: EconomicImpact = Field(default_factory=EconomicImpact)
    contradictions: List[str] = Field(default_factory=list)
    related_disclosures: List[str] = Field(default_factory=list)

class FinalReport(BaseModel):
    ticker: str
    critical_count: int = 0
    material_count: int = 0
    low_value_count: int = 0
    unread_count: int = 0

    most_important_developments: List[str] = Field(default_factory=list)
    real_value_points: List[str] = Field(default_factory=list)
    what_changed: List[str] = Field(default_factory=list)

    economic_impact: EconomicImpact = Field(default_factory=EconomicImpact)

    positive_findings: List[str] = Field(default_factory=list)
    negative_risky_findings: List[str] = Field(default_factory=list)
    unanswered_questions: List[EconomicQuestion] = Field(default_factory=list)

    general_evaluation: str = ""
    most_critical_conclusion: str = ""
