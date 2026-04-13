from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from litestar_pulse.db import initdb


async def initialize_cmsfix2_seed(
    session: AsyncSession, result_dict: dict[str, Any]
) -> bool:
    """
    Initializes the CMSFix2 database with seed data.

    Args:
        session (AsyncSession): The database session to use for seeding.
        result_dict (dict[str, Any]): A dictionary to store the results of the seeding process.

    Returns:
        bool: True if seeding was successful, False otherwise.
    """
    print("Seeding CMSFix2 database...")
    return True


async def initialize_database() -> dict[str, int]:
    """
    Initializes the database by creating all tables and optionally seeding it with initial data.

    Args:
        seed_module (Any): The module containing the seed data. Defaults to SEED.

    Returns:
        dict[str, int]: A dictionary containing the count of records in each table after initialization.
    """

    initdb.add_initdb_function(initialize_cmsfix2_seed)
    return await initdb.initialize_database()


# EOF
