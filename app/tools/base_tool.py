from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """
    Base class for all Hospital AI tools.

    A tool performs a specific, well-defined operation
    on behalf of an agent.

    Tools may retrieve information or request actions,
    but agents should not directly access database
    implementation details.
    """

    def __init__(
        self,
        tool_name: str,
        description: str,
    ) -> None:
        """
        Initialize the tool.

        Args:
            tool_name: Unique name of the tool.
            description: Human-readable description of
                         what the tool does.
        """

        if not tool_name.strip():
            raise ValueError(
                "tool_name cannot be empty."
            )

        if not description.strip():
            raise ValueError(
                "description cannot be empty."
            )

        self.tool_name = tool_name
        self.description = description

    # =========================================================
    # Public execution interface
    # =========================================================

    def run(
        self,
        **kwargs: Any,
    ) -> Any:
        """
        Execute the tool.

        The common interface is provided here while the
        actual implementation is provided by execute().
        """

        return self.execute(
            **kwargs
        )

    # =========================================================
    # Tool-specific implementation
    # =========================================================

    @abstractmethod
    def execute(
        self,
        **kwargs: Any,
    ) -> Any:
        """
        Perform the actual tool operation.

        Every concrete tool must implement this method.
        """

        raise NotImplementedError

    # =========================================================
    # Tool metadata
    # =========================================================

    def get_definition(self) -> dict[str, str]:
        """
        Return basic metadata describing the tool.
        """

        return {
            "name": self.tool_name,
            "description": self.description,
        }