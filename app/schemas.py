from pydantic import BaseModel, Field

class AnalyseRequest(BaseModel):
    transaction_id: int

class AlertAction(BaseModel):
    action: str = Field(pattern="^(acknowledge|dismiss|escalate)$")

class CaseStatusUpdate(BaseModel):
    status: str = Field(pattern="^(New|Under Review|Escalated|Resolved|Closed)$")

class CaseResolutionUpdate(BaseModel):
    resolution: str = Field(pattern="^(Confirmed Fraud|False Positive|Inconclusive)$")

class NoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)
    author: str = "Investigator"

class AssistantQuery(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
