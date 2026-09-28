from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionState:
    """
    Tracks the execution state of an agent workflow.

    ExecutionState is orchestration metadata.

    It does NOT:
        - execute agents
        - execute tools
        - access the database
        - modify AgentContext

    AgentContext contains the shared business/workflow data.
    ExecutionState contains the orchestration progress.
    """

    workflow_name: str

    status: str = "PENDING"

    current_agent: str | None = None

    completed_agents: list[str] = field(
        default_factory=list
    )

    failed_agents: list[str] = field(
        default_factory=list
    )

    execution_history: list[dict[str, Any]] = field(
        default_factory=list
    )

    error: str | None = None

    # =========================================================
    # START
    # =========================================================

    def start(self) -> None:
        """
        Mark workflow execution as started.
        """

        self.status = "RUNNING"
        self.error = None

    # =========================================================
    # SET CURRENT AGENT
    # =========================================================

    def set_current_agent(
        self,
        agent_name: str,
    ) -> None:
        """
        Set the agent currently being executed.
        """

        if not agent_name.strip():
            raise ValueError(
                "agent_name cannot be empty."
            )

        self.current_agent = agent_name

    # =========================================================
    # RECORD SUCCESS
    # =========================================================

    def record_agent_success(
        self,
        agent_name: str,
    ) -> None:
        """
        Record successful completion of an agent.
        """

        if not agent_name.strip():
            raise ValueError(
                "agent_name cannot be empty."
            )

        if agent_name not in self.completed_agents:
            self.completed_agents.append(
                agent_name
            )

        self.execution_history.append(
            {
                "agent": agent_name,
                "status": "SUCCESS",
            }
        )

        self.current_agent = None

    # =========================================================
    # RECORD FAILURE
    # =========================================================

    def record_agent_failure(
        self,
        agent_name: str,
        error: str,
    ) -> None:
        """
        Record failed execution of an agent.
        """

        if not agent_name.strip():
            raise ValueError(
                "agent_name cannot be empty."
            )

        if not error.strip():
            raise ValueError(
                "error cannot be empty."
            )

        if agent_name not in self.failed_agents:
            self.failed_agents.append(
                agent_name
            )

        self.execution_history.append(
            {
                "agent": agent_name,
                "status": "FAILED",
                "error": error,
            }
        )

        self.current_agent = None
        self.error = error

    # =========================================================
    # COMPLETE WORKFLOW
    # =========================================================

    def complete(self) -> None:
        """
        Mark workflow execution as completed.
        """

        self.status = "COMPLETED"
        self.current_agent = None

    # =========================================================
    # FAIL WORKFLOW
    # =========================================================

    def fail(
        self,
        error: str,
    ) -> None:
        """
        Mark workflow execution as failed.
        """

        if not error.strip():
            raise ValueError(
                "error cannot be empty."
            )

        self.status = "FAILED"
        self.error = error
        self.current_agent = None

    # =========================================================
    # STATUS HELPERS
    # =========================================================

    def is_running(self) -> bool:
        """
        Return True if workflow is currently running.
        """

        return self.status == "RUNNING"

    def is_completed(self) -> bool:
        """
        Return True if workflow completed successfully.
        """

        return self.status == "COMPLETED"

    def is_failed(self) -> bool:
        """
        Return True if workflow failed.
        """

        return self.status == "FAILED"

    # =========================================================
    # SERIALIZATION
    # =========================================================

    def to_dict(self) -> dict[str, Any]:
        """
        Return the execution state as a dictionary.
        """

        return {
            "workflow_name": self.workflow_name,
            "status": self.status,
            "current_agent": self.current_agent,
            "completed_agents": list(
                self.completed_agents
            ),
            "failed_agents": list(
                self.failed_agents
            ),
            "execution_history": list(
                self.execution_history
            ),
            "error": self.error,
        }