from app.models.agent_result import AgentResult


class AgentRouter:
    """
    Determines which agent should execute next based on
    the decision produced by the current agent.

    The router is responsible only for routing.

    It does NOT:
        - execute agents
        - execute tools
        - access the database
        - modify AgentContext
        - make medical decisions
    """

    # =========================================================
    # DEFAULT ROUTES
    # =========================================================

    DEFAULT_ROUTES: dict[str, str | None] = {

        # -----------------------------------------------------
        # Terminal routes
        # -----------------------------------------------------

        "NO_ACTION": None,
        "WAIT_FOR_RESULT": None,

        # -----------------------------------------------------
        # Lab routes
        # -----------------------------------------------------

        "LAB_ORDER_UPDATED": "LabAgent",

        "REVIEW_ABNORMAL_LAB": "LabAgent",

        "ESCALATE_CRITICAL_LAB": (
            "ClinicalEscalationAgent"
        ),
        "ESCALATION_COMPLETED": None,
        # -----------------------------------------------------
        # Emergency / hospital workflow routes
        # -----------------------------------------------------

        "REQUEST_TRANSPORT": "EmergencyAgent",

        "RESERVE_BED": "BedAgent",

        "ASSIGN_DOCTOR": "StaffAgent",

        "ASSIGN_NURSE": "StaffAgent",
    }

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(
        self,
        routes: dict[str, str | None] | None = None,
    ) -> None:

        if routes is None:
            routes = self.DEFAULT_ROUTES

        self.routes = dict(routes)

    # =========================================================
    # GET NEXT AGENT
    # =========================================================

    def get_next_agent(
        self,
        result: AgentResult,
    ) -> str | None:
        """
        Return the next agent associated with the result decision.

        Returns None only when the decision is explicitly mapped
        to None, for example:

            NO_ACTION -> None

        Raises ValueError when the decision is unknown.
        """

        if result is None:
            raise ValueError(
                "result cannot be None."
            )

        decision = result.decision

        if decision is None:
            raise ValueError(
                "Agent result does not contain a decision."
            )

        if not decision.strip():
            raise ValueError(
                "Agent result contains an empty decision."
            )

        if decision not in self.routes:
            raise ValueError(
                f"Unknown routing decision: {decision}"
            )

        return self.routes[decision]

    # =========================================================
    # IS KNOWN DECISION
    # =========================================================

    def is_known_decision(
        self,
        decision: str | None,
    ) -> bool:
        """
        Return True when the decision exists in the routing table.
        """

        if decision is None:
            return False

        if not decision.strip():
            return False

        return decision in self.routes

    # =========================================================
    # ADD ROUTE
    # =========================================================

    def add_route(
        self,
        decision: str,
        agent_name: str | None,
    ) -> None:
        """
        Add or update a routing rule.

        agent_name=None represents a valid terminal route.
        """

        if not decision.strip():
            raise ValueError(
                "decision cannot be empty."
            )

        self.routes[decision] = agent_name

    # =========================================================
    # REMOVE ROUTE
    # =========================================================

    def remove_route(
        self,
        decision: str,
    ) -> None:
        """
        Remove a routing rule.
        """

        if not decision.strip():
            raise ValueError(
                "decision cannot be empty."
            )

        self.routes.pop(
            decision,
            None,
        )

    # =========================================================
    # GET ROUTES
    # =========================================================

    def get_routes(
        self,
    ) -> dict[str, str | None]:

        return dict(
            self.routes
        )