from abc import ABC, abstractmethod
from typing import Any

from app.models.agent_context import AgentContext
from app.models.agent_result import AgentResult


class BaseAgent(ABC):
    """
    Base class for all Hospital AI agents.

    This class defines the common interface and execution
    lifecycle for specialized agents.

    It does NOT contain hospital-specific business logic.
    """

    def __init__(
        self,
        agent_name: str,
    ) -> None:
        """
        Initialize the agent.

        Args:
            agent_name: Unique name identifying the agent.
        """

        if not agent_name.strip():
            raise ValueError(
                "agent_name cannot be empty."
            )

        self.agent_name = agent_name

    # =========================================================
    # Public execution method
    # =========================================================

    def run(
        self,
        context: AgentContext,
    ) -> AgentResult:
        """
        Execute the agent using the supplied context.

        The base class controls the execution lifecycle,
        while the specialized agent provides the actual
        reasoning through the process() method.
        """

        if not isinstance(
            context,
            AgentContext,
        ):
            raise TypeError(
                "context must be an AgentContext instance."
            )

        try:
            result = self.process(context)

            if not isinstance(
                result,
                AgentResult,
            ):
                raise TypeError(
                    "process() must return an AgentResult."
                )

            return result

        except Exception as exc:

            error_message = (
                f"{self.agent_name} failed: {str(exc)}"
            )

            context.add_error(
                error_message
            )

            return AgentResult(
                status="FAILED",
                reason=error_message,
                errors=[
                    error_message
                ],
            )

    # =========================================================
    # Agent-specific processing
    # =========================================================

    @abstractmethod
    def process(
        self,
        context: AgentContext,
    ) -> AgentResult:
        """
        Perform the actual work of the specialized agent.

        Every specialized agent must implement this method.
        """

        raise NotImplementedError

    # =========================================================
    # Utility methods
    # =========================================================

    def create_result(
        self,
        status: str,
        decision: str | None = None,
        reason: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> AgentResult:
        """
        Create a standardized AgentResult.
        """

        return AgentResult(
            status=status,
            decision=decision,
            reason=reason,
            data=data or {},
        )

    def add_decision(
        self,
        context: AgentContext,
        decision: str,
        reason: str,
    ) -> None:
        """
        Record an agent decision in the shared context.
        """

        context.add_decision({
            "agent": self.agent_name,
            "decision": decision,
            "reason": reason,
        })

    def add_action(
        self,
        context: AgentContext,
        action: dict[str, Any],
    ) -> None:
        """
        Record an action in the shared context.
        """

        context.add_action(
            action
        )