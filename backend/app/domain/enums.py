from enum import StrEnum


class SignalType(StrEnum):
    DRIVER = "driver"
    BLOCKER = "blocker"


class EvidenceStrength(StrEnum):
    EXPLICIT = "explicit"
    IMPLIED = "implied"


class PipelineStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ReviewStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
