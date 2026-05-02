from __future__ import annotations

from collections.abc import Awaitable, Callable

from litestar import Litestar

from litestar_pulse.config.app import logger
from litestar_pulse.lib.app import init_app as lp_init_app


def init_app() -> Litestar:

    logger.info("Initializing CMSFix2 application...")

    return lp_init_app(lp_prefix="/_mgr")


# EOF
