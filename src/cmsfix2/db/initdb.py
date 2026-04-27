from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from litestar_pulse.db import handler_factory
from litestar_pulse.db import initdb, get_handler
from litestar_pulse.lib.app import logger

from .handler import CMSFix2Handler
from .fixtures import seed


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
    logger.info("Seeding CMSFix2 database...")
    dbh = handler_factory(session)
    assert dbh is not None, "Database handler is not initialized"

    # initialize additional EnumKeys and Groups from CMSFix2 seed data
    ok = await initdb.initialize_lp_seed(session, result_dict, seed)
    if not ok:
        logger.error("Failed to seed CMSFix2 database")
        return False

    # additional CMSFix2 specific seeding can be added here if needed
    site_payloads = normalize_site_payload(getattr(seed, "SITES", []))
    sites = await ensure_sites(site_payloads)
    result_dict["sites"] = sites

    return True


async def initialize_database(initialize: bool = True) -> dict[str, int]:
    """
    Initializes the database by creating all tables and optionally seeding it with initial data.

    Args:
        initialize (bool): Whether to initialize the database with seed data. Defaults to True.

    Returns:
        dict[str, int]: A dictionary containing the count of records in each table after initialization.
    """

    initdb.add_initdb_function(initialize_cmsfix2_seed)
    if initialize:
        return await initdb.initialize_database()
    return {}


def normalize_site_payload(
    payloads: list[tuple[str, str]],
) -> list[dict[str, Any]]:
    """
    Normalizes the site payloads into a list of dictionaries with 'fqdn' and 'groups' keys.

    Args:
        payloads (list[tuple[str, list[str]]]): A list of tuples containing site information. Each tuple should have a "name" and a list of "fqdn" values.

    Returns:
        list[dict[str, Any]]: A list of dictionaries with 'fqdn' and 'groups' keys.
    """
    normalized = []
    for fqdn, group_name in payloads:
        normalized.append({"fqdn": fqdn, "group": group_name})
    return normalized


async def ensure_sites(payloads: list[dict[str, Any]]) -> int:
    """
    Ensures that the specified sites exist in the database, creating them if necessary.

    Args:
        payloads (list[tuple[str, list[str]]]): A list of tuples containing site information. Each tuple should have a "name" and a list of "fqdn" values.
    """

    counter = 0
    dbh = get_handler()
    for site_dict in payloads:
        site = await dbh.service.Site.upsert_from_dict(site_dict, "fqdn")
        logger.info(
            f"Ensured site with FQDN '{site.fqdn}' owned by group: {site.group}"
        )
        counter += 1

    return counter


async def normalize_node_payload(
    payloads: list[Any],
) -> list[dict[str, Any]]:
    """
    Normalizes the node payloads by ensuring that each node dictionary contains a 'site_fqdn' key.

    Args:
        payloads (list[dict[str, Any]]): A list of dictionaries containing node information. Each dictionary should have a "name" and a "site_fqdn" key.

    Returns:
        list[dict[str, Any]]: A list of normalized node dictionaries with 'site_fqdn' keys.
    """
    normalized = []
    for node_item in payloads:
        if isinstance(node_item, dict):
            if "site_fqdn" not in node_item:
                logger.warning(f"Node payload is missing 'site_fqdn': {node_item}")
                continue
            normalized.append(node_item)
        elif isinstance(node_item, tuple) and len(node_item) == 2:
            name, site_fqdn = node_item
            normalized.append({"name": name, "site_fqdn": site_fqdn})
        else:
            logger.warning(f"Invalid node payload format: {node_item}")
    return normalized


async def ensure_nodes(payloads: list[dict[str, Any]]) -> int:
    """
    Ensures that the specified nodes exist in the database, creating them if necessary.

    Args:
        payloads (list[dict[str, Any]]): A list of dictionaries containing node information. Each dictionary should have a "name" and a "site_fqdn" key.

    Returns:
        int: The number of nodes that were ensured in the database.
    """

    counter = 0
    dbh = get_handler()
    for node_dict in payloads:
        site_fqdn = node_dict.pop("site_fqdn", None)
        if site_fqdn is None:
            logger.warning(f"Node payload is missing 'site_fqdn': {node_dict}")
            continue

        site = await dbh.repo.Site.get_by_field("fqdn", site_fqdn)
        if site is None:
            logger.warning(
                f"No site found with FQDN '{site_fqdn}' for node: {node_dict}"
            )
            continue

        node_dict["site_id"] = site.id
        node = await dbh.service.Node.upsert_from_dict(node_dict, "slug")
        logger.info(f"Ensured node with slug '{node.slug}' under site '{site.fqdn}'")
        counter += 1

    return counter


# EOF
