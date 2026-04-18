"""Progress tracking for indexing runs."""

from dataclasses import dataclass, field
from enum import Enum


class PipelineStage(str, Enum):
    """Pipeline stages for indexing."""

    SCANNING = "SCANNING"
    HASHING = "HASHING"
    PARSING = "PARSING"
    EXTRACTING = "EXTRACTING"
    RESOLVING = "RESOLVING"
    WRITING = "WRITING"
    EMBEDDING = "EMBEDDING"
    FINALIZING = "FINALIZING"


@dataclass
class Progress:
    """Tracks progress through pipeline stages."""

    current_stage: PipelineStage = PipelineStage.SCANNING
    files_processed: int = 0
    files_total: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def advance_stage(self, stage: PipelineStage) -> None:
        """Advance to the next pipeline stage."""
        self.current_stage = stage

    def add_error(self, error: str) -> None:
        """Record an error."""
        self.errors.append(error)

    def add_warning(self, warning: str) -> None:
        """Record a warning."""
        self.warnings.append(warning)

    @property
    def status(self) -> str:
        """Get current status string."""
        if self.errors:
            return "FAILED"
        return "RUNNING"
