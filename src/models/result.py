"""Processing result data model."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ResultStatus(Enum):
    """Status of trade processing."""
    SUCCESS = "success"
    REJECTED = "rejected"
    ERROR = "error"


@dataclass
class ProcessResult:
    """Result of processing a single trade through the pipeline.

    Attributes:
        trade_id: Identifier of the processed trade.
        status: Processing outcome status.
        matched_rules: List of rule names that were triggered.
        details: Additional information about the processing result.
        error_message: Error description if status is ERROR.
    """

    trade_id: str = ""
    status: ResultStatus = ResultStatus.SUCCESS
    matched_rules: list[str] = field(default_factory=list)
    details: str = ""
    error_message: Optional[str] = None

    @property
    def is_success(self) -> bool:
        """Check if processing was successful."""
        return self.status == ResultStatus.SUCCESS

    def __repr__(self) -> str:
        rules = ", ".join(self.matched_rules) if self.matched_rules else "none"
        return (
            f"ProcessResult(id={self.trade_id}, status={self.status.value}, "
            f"rules=[{rules}])"
        )
