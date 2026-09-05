from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime

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
    publish_date: datetime
    title: str
    content: Optional[str] = None
    url: Optional[str] = None
    is_correction: bool = False

    # Analysis outputs
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
