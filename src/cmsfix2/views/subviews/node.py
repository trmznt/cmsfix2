from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tagato import tags as t


class NodeFormModel:
    pass


class Node:
    """
    Main Node view
    """

    def __init__(self) -> None:
        pass

    async def index(self) -> dict[str, t.Tag | str]:
        """
        This method renders the page
        """
        raise NotImplementedError()

    async def view(self) -> dict[str, t.Tag | str | int]:
        """
        This method displays the node details
        """
        raise NotImplementedError()

    async def edit(self) -> dict[str, t.Tag | str | int]:
        """
        This method displays the edit form for the node
        """
        raise NotImplementedError()

    async def update(self, data: dict[str, Any]) -> str:
        """
        This method processes the update form submission
        """
        raise NotImplementedError()

    async def list(self, data: dict[str, Any]) -> str:
        """
        This method list the node content
        """
        raise NotImplementedError()


# EOF
