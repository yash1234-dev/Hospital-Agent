from typing import Any

from app.agents.base_agent import BaseAgent
from app.models.agent_context import AgentContext
from app.models.agent_result import AgentResult
from app.orchestration.execution_state import ExecutionState


class Orchestrator:
    """
    Coordinates execution of agents within a workflow.

    The Orchestrator is responsible for:

        - registering agents
        - finding registered agents
        - starting workflow execution
        - passing AgentContext to agents
        - recording execution state
        - handling agent success/failure
        - returning the final AgentResult

    The Orchestrator does NOT:

        - contain domain-specific business logic
        - access the database directly
        - execute tools directly
        - execute ActionGateway operations directly
        - make medical decisions
    """

    def __init__(
        self,
        workflow_name: str,
    ) -> None:

        if not workflow_name.strip():
            raise ValueError(
                "workflow_name cannot be empty."
            )

        self.workflow_name = workflow_name

        self.agents: dict[str, BaseAgent] = {}

        self.state = ExecutionState(
            workflow_name=workflow_name
        )

    # =========================================================
    # REGISTER AGENT
    # =========================================================

    def register_agent(
        self,
        agent: BaseAgent,
    ) -> None:
        """
        Register an agent with the orchestrator.
        """

        if agent is None:
            raise ValueError(
                "agent cannot be None."
            )

        agent_name = agent.agent_name

        if not agent_name.strip():
            raise ValueError(
                "Agent name cannot be empty."
            )

        if agent_name in self.agents:
            raise ValueError(
                f"Agent already registered: {agent_name}"
            )

        self.agents[agent_name] = agent

    # =========================================================
    # GET AGENT
    # =========================================================

    def get_agent(
        self,
        agent_name: str,
    ) -> BaseAgent:
        """
        Retrieve a registered agent by name.
        """

        if agent_name not in self.agents:
            raise ValueError(
                f"Agent is not registered: {agent_name}"
            )

        return self.agents[agent_name]

    # =========================================================
    # LIST AGENTS
    # =========================================================

    def list_agents(self) -> list[str]:
        """
        Return names of all registered agents.
        """

        return list(
            self.agents.keys()
        )

    # =========================================================
    # RUN SINGLE AGENT
    # =========================================================

    def run_agent(
        self,
        agent_name: str,
        context: AgentContext,
    ) -> AgentResult:
        """
        Execute one registered agent.

        The agent receives the shared AgentContext.

        ExecutionState is updated according to the
        AgentResult returned by the agent.
        """

        agent = self.get_agent(
            agent_name
        )

        # -----------------------------------------------------
        # Set current agent
        # -----------------------------------------------------

        self.state.set_current_agent(
            agent_name
        )

        try:

            # -------------------------------------------------
            # Execute agent
            # -------------------------------------------------

            result = agent.run(
                context
            )

            # -------------------------------------------------
            # Record result
            # -------------------------------------------------

            if result.is_success():

                self.state.record_agent_success(
                    agent_name
                )

            else:

                self.state.record_agent_failure(
                    agent_name,
                    result.reason
                    or "Agent execution failed.",
                )

            return result

        except Exception as exc:

            # -------------------------------------------------
            # Defensive failure boundary
            # -------------------------------------------------

            error_message = (
                f"{agent_name} failed: {exc}"
            )

            self.state.record_agent_failure(
                agent_name,
                error_message,
            )

            raise

    # =========================================================
    # RUN WORKFLOW
    # =========================================================

    def run(
        self,
        context: AgentContext,
        agent_sequence: list[str],
    ) -> AgentResult:
        """
        Execute a predefined sequence of agents.

        Example:

            [
                "TriageAgent",
                "EmergencyAgent",
                "BedAgent",
                "StaffAgent"
            ]

        The workflow stops when an agent fails.
        """

        if context is None:
            raise ValueError(
                "context cannot be None."
            )

        if not agent_sequence:
            raise ValueError(
                "agent_sequence cannot be empty."
            )

        # -----------------------------------------------------
        # Validate agents before execution
        # -----------------------------------------------------

        for agent_name in agent_sequence:

            if agent_name not in self.agents:

                raise ValueError(
                    f"Agent is not registered: "
                    f"{agent_name}"
                )

        # -----------------------------------------------------
        # Start workflow
        # -----------------------------------------------------

        self.state.start()

        last_result: AgentResult | None = None

        # -----------------------------------------------------
        # Execute agents sequentially
        # -----------------------------------------------------

        for agent_name in agent_sequence:

            result = self.run_agent(
                agent_name,
                context,
            )

            last_result = result

            # -------------------------------------------------
            # Stop if agent failed
            # -------------------------------------------------

            if not result.is_success():

                self.state.fail(
                    result.reason
                    or f"{agent_name} failed."
                )

                return result

        # -----------------------------------------------------
        # Complete workflow
        # -----------------------------------------------------

        self.state.complete()

        # This cannot normally be None because we reject an
        # empty agent_sequence above.
        return last_result
        # =========================================================
    # RUN DYNAMIC WORKFLOW
    # =========================================================

    def run_dynamic(
        self,
        context: AgentContext,
        initial_agent: str,
        router,
        max_steps: int = 10,
    ) -> AgentResult:
        """
        Execute agents dynamically using an AgentRouter.

        The first agent is explicitly provided.

        After each successful agent execution, the router
        examines the AgentResult and determines which agent
        should execute next.

        Execution stops when:

            - a valid terminal decision is returned
            - an agent fails
            - an invalid routing decision is produced
            - the router selects an unregistered agent
            - an already executed agent is selected
            - max_steps is reached

        The same agent cannot execute more than once within
        a single dynamic workflow execution.
        """

        if context is None:
            raise ValueError(
                "context cannot be None."
            )

        if not initial_agent.strip():
            raise ValueError(
                "initial_agent cannot be empty."
            )

        if router is None:
            raise ValueError(
                "router cannot be None."
            )

        if max_steps <= 0:
            raise ValueError(
                "max_steps must be greater than zero."
            )

        # -----------------------------------------------------
        # Validate initial agent
        # -----------------------------------------------------

        if initial_agent not in self.agents:

            raise ValueError(
                f"Agent is not registered: "
                f"{initial_agent}"
            )

        # -----------------------------------------------------
        # Start workflow
        # -----------------------------------------------------

        self.state.start()

        current_agent = initial_agent

        # -----------------------------------------------------
        # Dynamic execution loop
        # -----------------------------------------------------

        for step in range(max_steps):

            # -------------------------------------------------
            # Loop protection before execution
            # -------------------------------------------------

            if current_agent in self.state.completed_agents:

                error_message = (
                    f"Agent execution loop detected: "
                    f"{current_agent} has already completed "
                    f"in this workflow."
                )

                self.state.fail(
                    error_message
                )

                return AgentResult(
                    status="FAILED",
                    decision=None,
                    reason=error_message,
                    errors=[
                        error_message
                    ],
                )

            # -------------------------------------------------
            # Execute current agent
            # -------------------------------------------------

            result = self.run_agent(
                current_agent,
                context,
            )
            if result.is_success() and result.decision:
               context.add_decision({
                   "agent": current_agent,
                   "decision": result.decision,
                   "reason": result.reason,
    })
            # -------------------------------------------------
            # Stop on agent failure
            # -------------------------------------------------

            if not result.is_success():

                self.state.fail(
                    result.reason
                    or f"{current_agent} failed."
                )

                return result

            # -------------------------------------------------
            # Ask router for next agent
            # -------------------------------------------------

            try:

                next_agent = router.get_next_agent(
                    result
                )

            except Exception as exc:

                error_message = (
                    f"Routing failed after "
                    f"{current_agent}: {exc}"
                )

                self.state.fail(
                    error_message
                )

                return AgentResult(
                    status="FAILED",
                    decision=None,
                    reason=error_message,
                    errors=[
                        error_message
                    ],
                )

            # -------------------------------------------------
            # Valid terminal decision
            # -------------------------------------------------

            if next_agent is None:

                self.state.complete()

                return result

            # -------------------------------------------------
            # Validate next agent
            # -------------------------------------------------

            if next_agent not in self.agents:

                error_message = (
                    f"Router selected unregistered "
                    f"agent: {next_agent}"
                )

                self.state.fail(
                    error_message
                )

                return AgentResult(
                    status="FAILED",
                    decision=None,
                    reason=error_message,
                    errors=[
                        error_message
                    ],
                )

            # -------------------------------------------------
            # Loop protection for next agent
            # -------------------------------------------------

            if next_agent in self.state.completed_agents:

                error_message = (
                    f"Agent execution loop detected: "
                    f"router selected already completed "
                    f"agent {next_agent}."
                )

                self.state.fail(
                    error_message
                )

                return AgentResult(
                    status="FAILED",
                    decision=None,
                    reason=error_message,
                    errors=[
                        error_message
                    ],
                )

            # -------------------------------------------------
            # Continue workflow
            # -------------------------------------------------

            current_agent = next_agent

        # -----------------------------------------------------
        # Maximum step protection
        # -----------------------------------------------------

        error_message = (
            f"Maximum orchestration steps exceeded: "
            f"{max_steps}"
        )

        self.state.fail(
            error_message
        )

        return AgentResult(
            status="FAILED",
            decision=None,
            reason=error_message,
            errors=[
                error_message
            ],
        )
    # =========================================================
    # GET EXECUTION STATE
    # =========================================================

    def get_state(self) -> ExecutionState:
        """
        Return the current workflow execution state.
        """

        return self.state

    # =========================================================
    # GET STATE DICTIONARY
    # =========================================================

    def get_state_dict(self) -> dict[str, Any]:
        """
        Return the current execution state as a dictionary.
        """

        return self.state.to_dict()