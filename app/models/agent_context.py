from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentContext:
    """
    Shared execution context passed between agents.

    The context contains the information that agents need
    while processing a hospital operation.

    It is intentionally independent of any specific agent.
    """

    # =========================================================
    # Core identifiers
    # =========================================================

    patient_id: str | None = None

    incident_id: int | None = None

    admission_id: int | None = None

    department_id: int | None = None

    # =========================================================
    # Shared data
    # =========================================================

    data: dict[str, Any] = field(default_factory=dict)

    # =========================================================
    # Agent decisions
    # =========================================================

    decisions: list[dict[str, Any]] = field(
        default_factory=list
    )

    # =========================================================
    # Actions requested/executed
    # =========================================================

    actions: list[dict[str, Any]] = field(
        default_factory=list
    )

    # =========================================================
    # Errors encountered during execution
    # =========================================================

    errors: list[str] = field(
        default_factory=list
    )

    # =========================================================
    # Utility methods
    # =========================================================

    def add_data(
        self,
        key: str,
        value: Any,
    ) -> None:
        """
        Store shared information in the context.
        """

        self.data[key] = value

    def add_decision(
        self,
        decision: dict[str, Any],
    ) -> None:
        """
        Add an agent decision to the context.
        """

        self.decisions.append(decision)

    def add_action(
        self,
        action: dict[str, Any],
    ) -> None:
        """
        Record an action requested or executed by an agent.
        """

        self.actions.append(action)

    def add_error(
        self,
        error: str,
    ) -> None:
        """
        Record an error encountered during execution.
        """

        self.errors.append(error)

    def has_errors(self) -> bool:
        """
        Return True if one or more errors exist.
        """

        return len(self.errors) > 0