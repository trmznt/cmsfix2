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

from litestar_pulse.db import handler, set_handler_class

from .models import node


class Model(handler.Model):
    Node = node.Node


class SiteRepo(SQLAlchemyAsyncRepository[node.Site]):
    model_type = node.Site


class SiteService(handler.LPBaseService[node.Site]):
    repository_type = SiteRepo

    async def before_update_from_dict(self, instance: node.Site, data: dict) -> None:

        if self.handler is None:
            raise ValueError("Handler is not set for SiteService")

        # check if data contains "group" or "group_id", since they are mutually exclusive,
        # we can check for either one to determine if group update is needed
        if "group" in data and "group_id" in data:
            raise ValueError(
                "Updating site requires group_id or group field, but not both"
            )
        if "group" in data:
            data["group"] = await self.handler.normalize_groups(data["group"])

        return await super().before_update_from_dict(instance, data)


class NodeRepo(SQLAlchemyAsyncRepository[node.Node]):
    model_type = node.Node


class NodeService(handler.LPBaseService[node.Node]):
    repository_type = NodeRepo


class CMSFix2Handler(handler.LPHandler):

    model = Model()

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session)  # type: ignore

        self.repo.Site = lop.Proxy(lambda: SiteRepo(session=self.session))
        self.service.Site = lop.Proxy(
            lambda: SiteService(
                session=self.session,
                repository=self.repo.Site.__wrapped__,
                handler=self,
            )
        )

        self.repo.Node = lop.Proxy(lambda: NodeRepo(session=self.session))
        self.service.Node = lop.Proxy(
            lambda: NodeService(
                session=self.session,
                repository=self.repo.Node.__wrapped__,
                handler=self,
            )
        )


set_handler_class(CMSFix2Handler)

# EOF
