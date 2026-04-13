# SPDX-FileCopyrightText: 2026 Hidayat Trimarsanto <trimarsanto@gmail.com>
# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations

__copyright__ = "(C) 2026 Hidayat Trimarsanto <trimarsanto@gmail.com>"
__author__ = "trimarsanto@gmail.com"
__license__ = "MPL-2.0"

from sqlalchemy.ext.asyncio import AsyncSession

from advanced_alchemy.repository import SQLAlchemyAsyncRepository
from advanced_alchemy.service import SQLAlchemyAsyncRepositoryService

import lazy_object_proxy as lop

from litestar_pulse.db import handler

from .models import node


class Model(handler.Model):
    Node = node.Node


class NodeRepo(SQLAlchemyAsyncRepository[node.Node]):
    model_type = node.Node


class NodeService(SQLAlchemyAsyncRepositoryService[node.Node]):
    repository_type = NodeRepo


class CMSFix2Handler(handler.LPHandler):

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session)

        self.repo.Node = lop.Proxy(lambda: NodeRepo(session=self.session))
        self.service.Node = lop.Proxy(
            lambda: NodeService(
                session=self.session, repository=self.repo.Node.__wrapped__
            )
        )


# EOF
