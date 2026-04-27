# SPDX-FileCopyrightText: 2025 Hidayat Trimarsanto <trimarsanto@gmail.com>
# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations


__copyright__ = "(C) 2025 Hidayat Trimarsanto <trimarsanto@gmail.com>"
__author__ = "trimarsanto@gmail.com"
__license__ = "MPL-2.0"


from os import path
from uuid import UUID
import json

from markupsafe import Markup, escape

from sqlalchemy.ext.asyncio import AsyncSession

from litestar import Controller, Request, Response, get, post, patch, delete, MediaType
from litestar.response import Redirect, File
from litestar.handlers import HTTPRouteHandler
from litestar.status_codes import HTTP_303_SEE_OTHER
from litestar.handlers.base import BaseRouteHandler
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException

from litestar_pulse.config.app import logger, general_config
from litestar_pulse.db import set_handler
from litestar_pulse.db.handler import handler_factory
from litestar_pulse.db.models.coremixins import RoleMixin
from litestar_pulse.lib.template import Template
from litestar_pulse.lib import roles as r
from litestar_pulse.lib.fileupload import FileUploadProxy
from litestar_pulse.views.baseview import LPController

from ..db.handler import CMSFix2Handler
from . import get_subview, get_form_model

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tagato import tags as t
    from litestar.datastructures import FormMultiDict, MultiDict
    from ..db.models.node import Node as Node


class NodeView(LPController):
    """
    Controller that will redirect all Node related views to subviews.
    """

    path = "/"
    model_type = CMSFix2Handler.model.Node

    model_form = get_form_model

    # it  path starts with uuid=, then load the node with that uuid
    async def resolve_node(self, path: str, db_session: AsyncSession) -> Node | None:
        if path.startswith("uuid="):
            uuid_str = path[len("uuid=") :]
            try:
                node_uuid = UUID(uuid_str)
            except ValueError:
                logger.error(f"Invalid UUID in path: {path}")
                return None
            dbh = handler_factory(db_session)
            assert dbh is not None, "Database handler is not initialized"
            node = await dbh.get_node_by_uuid(node_uuid)
            if node is None:
                logger.error(f"No node found with UUID: {node_uuid}")
            return node
        return None

    @get(path="/{path:path}", name="index", guards=[LPController.viewing_role_guard])
    async def index_html(
        self,
        path: str,
        request: Request,
        db_session: AsyncSession,
        transaction: AsyncSession,
    ) -> dict[str, t.Tag | str]:
        self.init_view(request, db_session, transaction)
        node = await self.resolve_node(path, db_session)
        if node is None:
            return {
                "content": Markup(f"<p>Node not found for path: {escape(path)}</p>")
            }
        subview_cls = get_subview(type(node))
        if subview_cls is None:
            return {
                "content": Markup(
                    f"<p>No view registered for node type: {escape(type(node).__name__)}</p>"
                )
            }
        return subview_cls()

        raise NotImplementedError()

    @get(
        path="/{path:path}/._view",
        name="view",
        guards=[LPController.viewing_role_guard],
    )
    async def view_html(
        self,
        path: str,
        request: Request,
        db_session: AsyncSession,
        transaction: AsyncSession,
    ) -> dict[str, t.Tag | str | int]:
        raise NotImplementedError()

    @get(
        path="/{path:path}/._edit",
        name="edit",
        guards=[LPController.viewing_role_guard],
    )
    async def edit_html(
        self,
        path: str,
        request: Request,
        db_session: AsyncSession,
        transaction: AsyncSession,
    ) -> dict[str, t.Tag | str | int]:
        raise NotImplementedError()

    @post(
        path="/{path:path}/._update",
        name="update",
        guards=[LPController.managing_role_guard],
    )
    async def update_html(
        self,
        path: str,
        request: Request,
        db_session: AsyncSession,
        transaction: AsyncSession,
        data: MultiDict[Any] | dict[str, Any] = {},
    ) -> Response[str] | Template:
        raise NotImplementedError()


# EOF
