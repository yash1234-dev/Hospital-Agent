from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    """
    Standardized result returned by an agent.

    Every specialized agent should eventually return
    an AgentResult instead of an arbitrary string or dictionary.
    """

    # =========================================================
    # Execution status
    # =========================================================

    status: str

    # =========================================================
    # Agent's primary decision
    # =========================================================

    decision: str | None = None

    # =========================================================
    # Explanation for the decision
    # =========================================================

    reason: str | None = None

    # =========================================================
    # Data produced or retrieved by the agent
    # =========================================================

    data: dict[str, Any] = field(
        default_factory=dict
    )

    # =========================================================
    # Actions requested or executed
    # =========================================================

    actions: list[dict[str, Any]] = field(
        default_factory=list
    )

    # =========================================================
    # Errors encountered
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
        Add information to the result.
        """

        self.data[key] = value

    def add_action(
        self,
        action: dict[str, Any],
    ) -> None:
        """
        Add an action to the result.
        """

        self.actions.append(action)

    def add_error(
        self,
        error: str,
    ) -> None:
        """
        Add an error to the result.
        """

        self.errors.append(error)

    def has_errors(self) -> bool:
        """
        Return True if the result contains errors.
        """

        return len(self.errors) > 0

    def is_success(self) -> bool:
        """
        Return True when the agent completed successfully.
        """

        return self.status == "SUCCESS"