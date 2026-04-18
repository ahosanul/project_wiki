"""State machine for indexing runs."""

from enum import Enum


class ProjectState(str, Enum):
    """Valid project states."""

    NEW = "NEW"
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


# Valid transitions for starting a run
VALID_START_STATES = {
    ProjectState.NEW,
    ProjectState.IDLE,
    ProjectState.COMPLETED,
    ProjectState.PARTIAL,
    ProjectState.FAILED,
}


def can_start_run(current_state: str) -> bool:
    """Check if a run can be started from the current state."""
    try:
        state = ProjectState(current_state)
        return state in VALID_START_STATES
    except ValueError:
        return False


def transition_to_running(state: str) -> str:
    """Transition state to RUNNING."""
    if not can_start_run(state):
        raise ValueError(f"Cannot start run from state: {state}")
    return ProjectState.RUNNING.value


def transition_to_completed(state: str) -> str:
    """Transition state to COMPLETED."""
    if state != ProjectState.RUNNING.value:
        raise ValueError(f"Can only transition to COMPLETED from RUNNING, got: {state}")
    return ProjectState.COMPLETED.value


def transition_to_failed(state: str) -> str:
    """Transition state to FAILED."""
    if state != ProjectState.RUNNING.value:
        raise ValueError(f"Can only transition to FAILED from RUNNING, got: {state}")
    return ProjectState.FAILED.value


def transition_to_partial(state: str) -> str:
    """Transition state to PARTIAL."""
    if state != ProjectState.RUNNING.value:
        raise ValueError(f"Can only transition to PARTIAL from RUNNING, got: {state}")
    return ProjectState.PARTIAL.value


def transition_to_idle(state: str) -> str:
    """Transition state to IDLE (after completion)."""
    if state not in {ProjectState.COMPLETED.value, ProjectState.FAILED.value}:
        raise ValueError(
            f"Can only transition to IDLE from COMPLETED or FAILED, got: {state}"
        )
    return ProjectState.IDLE.value
