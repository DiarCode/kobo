from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class WorkspaceRole(str, Enum):
    owner = "owner"
    admin = "admin"
    member = "member"


class TaskStatus(str, Enum):
    backlog = "backlog"
    todo = "todo"
    in_progress = "in_progress"
    blocked = "blocked"
    review = "review"
    done = "done"
    canceled = "canceled"


class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    urgent = "urgent"


class ArtifactType(str, Enum):
    spec = "spec"
    pr = "pr"
    code = "code"
    decision = "decision"
    design = "design"
    launch = "launch"
    note = "note"
    report = "report"


class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class RunStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    canceled = "canceled"


class APIMessage(BaseModel):
    message: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserRegisterIn(BaseModel):
    username: str
    password: str = Field(min_length=8)


class UserLoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: str
    username: str
    created_at: datetime


class AuthOut(BaseModel):
    user: UserOut


class WorkspaceCreateIn(BaseModel):
    name: str
    slug: str
    description: str | None = None
    template: str | None = None


class WorkspaceSettingsUpdateIn(BaseModel):
    name: str | None = None
    description: str | None = None
    template: str | None = None


class WorkspaceOut(BaseModel):
    id: str
    name: str
    slug: str
    description: str | None = None
    template: str | None = None
    invite_token: str | None = None
    created_at: datetime


class WorkspaceMemberOut(BaseModel):
    workspace_id: str
    user_id: str
    role: WorkspaceRole
    username: str | None = None
    nickname: str | None = None
    avatar_key: str | None = None


class ProjectCreateIn(BaseModel):
    workspace_id: str
    name: str
    description: str | None = None


class ProjectOut(BaseModel):
    id: str
    workspace_id: str
    name: str
    description: str | None
    created_at: datetime


class TaskCreateIn(BaseModel):
    workspace_id: str
    project_id: str | None = None
    title: str
    description: str | None = None
    status: str = "todo"
    priority: TaskPriority = TaskPriority.medium
    acceptance_criteria: list[str] = Field(default_factory=list)
    assignee_user_id: str | None = None
    assignee_agent_role: str | None = None


class TaskUpdateIn(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: TaskPriority | None = None
    acceptance_criteria: list[str] | None = None
    assignee_user_id: str | None = None
    assignee_agent_role: str | None = None
    proof_exempt: bool | None = None


class TaskOut(BaseModel):
    id: str
    workspace_id: str
    project_id: str | None
    title: str
    description: str | None
    status: str
    priority: TaskPriority
    acceptance_criteria: list[str]
    assignee_user_id: str | None
    assignee_agent_role: str | None
    proof_exempt: bool
    created_at: datetime
    updated_at: datetime


class TaskCommentCreateIn(BaseModel):
    content: str = Field(min_length=1)


class TaskCommentOut(BaseModel):
    id: str
    task_id: str
    author_user_id: str
    author_username: str
    content: str
    created_at: datetime


class TaskAttachmentCreateIn(BaseModel):
    file_name: str = Field(min_length=1)
    url: str = Field(min_length=1)
    mime_type: str | None = None


class TaskAttachmentOut(BaseModel):
    id: str
    task_id: str
    author_user_id: str
    author_username: str
    file_name: str
    url: str
    mime_type: str | None = None
    created_at: datetime


class TaskSubtaskCreateIn(BaseModel):
    title: str = Field(min_length=1)
    description: str | None = None
    assignee_user_id: str | None = None
    assignee_agent_role: str | None = None
    order: int | None = None


class TaskSubtaskUpdateIn(BaseModel):
    title: str | None = None
    description: str | None = None
    status: Literal["todo", "in_progress", "done"] | None = None
    assignee_user_id: str | None = None
    assignee_agent_role: str | None = None
    order: int | None = None


class TaskSubtaskOut(BaseModel):
    id: str
    task_id: str
    workspace_id: str
    title: str
    description: str | None = None
    status: Literal["todo", "in_progress", "done"]
    order: int
    assignee_user_id: str | None = None
    assignee_agent_role: str | None = None
    created_at: datetime
    updated_at: datetime


class TaskAgentRevisionIn(BaseModel):
    instruction: str = Field(min_length=1)
    stakes_level: Literal["low", "medium", "high", "irreversible"] = "medium"


class DependencyCreateIn(BaseModel):
    depends_on_task_id: str


class ActivityItem(BaseModel):
    id: str
    type: str
    content: str
    created_at: datetime


class ProofCheckOut(BaseModel):
    task_id: str
    has_artifact: bool
    proof_exempt: bool
    can_mark_done: bool


class ArtifactCreateIn(BaseModel):
    workspace_id: str
    task_id: str | None = None
    type: ArtifactType
    title: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactUpdateIn(BaseModel):
    title: str | None = None
    content: str | None = None
    metadata: dict[str, Any] | None = None


class ArtifactOut(BaseModel):
    id: str
    workspace_id: str
    task_id: str | None
    type: ArtifactType
    title: str
    content: str
    metadata: dict[str, Any]
    created_at: datetime


class EvidenceRef(BaseModel):
    id: str
    source_type: str
    source_ref: str
    confidence: float


class GroundedClaim(BaseModel):
    claim: str
    evidence_links: list[EvidenceRef]


class Assumption(BaseModel):
    text: str
    type: Literal["factual", "scope", "user_preference", "technical", "timeline"]
    risk: Literal["low", "medium", "high"]
    verification_suggestion: str


class ConfidenceBreakdown(BaseModel):
    source_ratio: float
    consistency: float
    verifier_risk: float


class AgentOutput(BaseModel):
    executive_summary: str
    full_content: str
    grounded_claims: list[GroundedClaim]
    assumptions: list[Assumption]
    confidence_score: float
    confidence_breakdown: ConfidenceBreakdown
    open_questions: list[str]
    review_flags: list[str]


class CritiqueReport(BaseModel):
    run_id: str
    unsupported_claims: list[str]
    contradictions: list[str]
    missing_constraints: list[str]
    verifier_notes: list[str]


class VerifierReport(BaseModel):
    run_id: str
    schema_valid: bool
    confidence_ok: bool
    assumption_density_ok: bool
    needs_escalation: bool


class AgentRunCreateIn(BaseModel):
    workspace_id: str
    task_id: str | None = None
    role_key: str
    goal: str
    stakes_level: Literal["low", "medium", "high", "irreversible"] = "medium"


class AgentRunOut(BaseModel):
    id: str
    workspace_id: str
    task_id: str | None
    role_key: str
    status: RunStatus
    output: AgentOutput | None = None
    created_at: datetime
    updated_at: datetime


class AgentRunTimelineOut(BaseModel):
    id: str
    run_id: str
    task_id: str | None = None
    workspace_id: str
    stage: Literal[
        "router",
        "planner",
        "retrieve",
        "execute",
        "critic",
        "verifier",
        "approval_gate",
        "committer",
    ]
    agent_role: str
    title: str
    summary: str
    status: Literal["running", "completed", "failed", "abstained"]
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskAgentTimelineOut(AgentRunTimelineOut):
    pass


class AgentMessage(BaseModel):
    message_id: str
    from_agent: str
    to_agent: str
    task_id: str
    message_type: Literal[
        "request",
        "response",
        "critique",
        "clarification",
        "escalation",
        "position",
        "completion",
    ]
    content: AgentOutput
    requires_ack: bool
    timestamp: datetime
    evidence_chain: list[str]


class CouncilCreateIn(BaseModel):
    workspace_id: str
    question: str
    task_id: str | None = None


class DecisionArtifactOut(BaseModel):
    id: str
    workspace_id: str
    question: str
    recommendation: str
    dissenting_views: list[str]
    confidence: float
    consensus_score: float
    created_at: datetime
    final_decision: str | None = None
    rationale: str | None = None


class CouncilSessionOut(BaseModel):
    id: str
    workspace_id: str
    status: RunStatus
    stage: str
    decision: DecisionArtifactOut | None


class ApprovalActionPlan(BaseModel):
    action_type: str
    target: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)


class ApprovalCreateIn(BaseModel):
    workspace_id: str
    task_id: str | None = None
    action_plan: ApprovalActionPlan
    diff_preview: dict[str, Any] | None = None


class ApprovalOut(BaseModel):
    id: str
    workspace_id: str
    task_id: str | None
    status: ApprovalStatus
    action_plan: ApprovalActionPlan
    diff_preview: dict[str, Any] | None = None
    decision_note: str | None = None
    created_at: datetime


class ApprovalDecisionIn(BaseModel):
    note: str | None = None


class SearchHybridIn(BaseModel):
    workspace_id: str
    query: str
    top_k: int = 8


class SearchResultOut(BaseModel):
    source_type: str
    source_ref: str
    score: float
    excerpt: str


class EvidencePackOut(BaseModel):
    query: str
    results: list[SearchResultOut]
    context_budget_tokens: int


class IntegrationConnectOut(BaseModel):
    provider: str
    authorize_url: str


class IntegrationActionIn(BaseModel):
    workspace_id: str
    task_id: str
    title: str
    description: str


class HealthDependency(BaseModel):
    status: Literal["ok", "degraded", "unknown"]
    detail: str


class HealthOut(BaseModel):
    service: str
    environment: str
    version: str
    dependencies: dict[str, HealthDependency]


class AutonomyScore(BaseModel):
    workspace_id: str
    role_key: str
    action_type: str
    score: float
    lower_bound95: float
    tier: Literal["tier0", "tier1", "tier2", "tier3"]
    sample_size: int


class EvalRunOut(BaseModel):
    id: str
    workspace_id: str
    run_type: str
    grounding_rate: float | None = None
    first_pass_approval: float | None = None
    unsupported_claim_rate: float | None = None
    p95_latency_ms: int | None = None
    cost_per_task: float | None = None
    created_at: datetime


class WorkspaceAgentCreateIn(BaseModel):
    role_key: str
    full_name: str | None = None
    system_prompt: str | None = None
    tone: str | None = None
    character: str | None = None
    avatar_key: str | None = None
    status: Literal["offline", "online", "working", "idle"] = "online"


class WorkspaceAgentBulkCreateIn(BaseModel):
    agents: list[WorkspaceAgentCreateIn]


class WorkspaceAgentUpdateIn(BaseModel):
    full_name: str | None = None
    status: Literal["offline", "online", "working", "idle"] | None = None
    tone: str | None = None
    character: str | None = None
    system_prompt: str | None = None
    avatar_key: str | None = None


class WorkspaceAgentOut(BaseModel):
    id: str
    workspace_id: str
    role_key: str
    full_name: str
    system_prompt: str
    tone: str
    character: str
    avatar_key: str
    status: Literal["offline", "online", "working", "idle"]
    created_at: datetime


class WorkspaceProfileUpdateIn(BaseModel):
    nickname: str = Field(min_length=1)
    avatar_key: str = Field(min_length=1)


class WorkspaceProfileOut(BaseModel):
    workspace_id: str
    user_id: str
    nickname: str
    avatar_key: str
    updated_at: datetime


class AssistantChatIn(BaseModel):
    message: str = Field(min_length=1)
    task_id: str | None = None
    include_history: bool = True


class AssistantHistoryItemOut(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    role: Literal["user", "assistant"]
    content: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)


class AssistantChatOut(BaseModel):
    message_id: str
    workspace_id: str
    response: str
    used_context: list[str] = Field(default_factory=list)
    model: str | None = None
    fallback_used: bool = False
    warning: str | None = None
    created_at: datetime


class AssistantVoiceTokenOut(BaseModel):
    workspace_id: str
    identity: str
    room: str
    token: str
    livekit_url: str


class WorkspaceInviteOut(BaseModel):
    workspace_id: str
    token: str
    invite_url: str
    created_at: datetime
    revoked: bool = False


class TaskStatusCreateIn(BaseModel):
    key: str = Field(min_length=1)
    label: str = Field(min_length=1)


class TaskStatusUpdateIn(BaseModel):
    label: str | None = Field(default=None, min_length=1)
    order: int | None = Field(default=None, ge=0)


class TaskStatusOut(BaseModel):
    key: str
    label: str
    order: int
    is_default: bool


class WorkspaceFileCreateIn(BaseModel):
    name: str = Field(min_length=1)
    url: str = Field(min_length=1)
    type: str = "doc"


class FileProcessingStatus(str, Enum):
    """File processing status enum."""
    uploading = "uploading"
    processing = "processing"
    extracting_text = "extracting_text"
    embedding = "embedding"
    completed = "completed"
    failed = "failed"


class WorkspaceFileOut(BaseModel):
    id: str
    workspace_id: str
    name: str
    url: str
    type: str
    processing_status: FileProcessingStatus = FileProcessingStatus.completed
    processing_error: str | None = None
    embedding_status: str | None = None
    uploaded_by_user_id: str
    created_at: datetime
    updated_at: datetime | None = None


class ActionRequiredCreateIn(BaseModel):
    title: str = Field(min_length=1)
    description: str
    severity: Literal["low", "medium", "high"] = "medium"


class ActionRequiredUpdateIn(BaseModel):
    status: Literal["open", "acknowledged", "done"]


class ActionRequiredOut(BaseModel):
    id: str
    workspace_id: str
    title: str
    description: str
    severity: Literal["low", "medium", "high"]
    status: Literal["open", "acknowledged", "done"]
    created_at: datetime
