from __future__ import annotations

from collections.abc import Awaitable, Callable

from litestar import Litestar

from litestar_pulse.config.app import logger
from litestar_pulse.lib.app import init_app as lp_init_app
from litestar_pulse.db import set_initdb_function_factory


def cmsfix2_initdb_function_factory() -> Callable[..., Awaitable[dict[str, int]]]:

    from ..db.initdb import initialize_database

    return initialize_database


def init_app() -> Litestar:

    logger.info("Initializing CMSFix2 application...")

    set_initdb_function_factory(cmsfix2_initdb_function_factory())

    return lp_init_app(
        lp_prefix="/_mgr", initdb_function_factory=cmsfix2_initdb_function_factory
    )


# EOF
