# SPDX-FileCopyrightText: 2026 Hidayat Trimarsanto <trimarsanto@gmail.com>
# SPDX-License-Identifier: MPL-2.0

from __future__ import annotations

__copyright__ = "(C) 2026 Hidayat Trimarsanto <trimarsanto@gmail.com>"
__author__ = "trimarsanto@gmail.com"
__license__ = "MPL-2.0"

from litestar_pulse.cli.commands import NoReturn, pulsemgr, get_dbhandler

import click


class RebrandedGroup(pulsemgr.__class__):
    def __init__(self, *args, **kwargs):
        # 1. Properly initialize the group with all Click-passed attributes
        super().__init__(*args, **kwargs)

        # 2. Merge parameters (options/arguments) from the existing group
        # This preserves the original options for the new brand
        self.params.extend(pulsemgr.params)

        # 3. Inherit all existing subcommands into this top-level group
        for cmd_name, cmd_obj in pulsemgr.commands.items():
            self.add_command(cmd_obj, name=cmd_name)


@click.group(cls=RebrandedGroup, name="cmsfix2mgr")
def cmsfix2mgr(use_ipdb: bool):
    """This new group now has all the old options and commands."""
    from litestar_pulse.db import set_initdb_function
    from ..db.handler import CMSFix2Handler
    from ..db.initdb import initialize_database

    click.echo("Initializing CMSFix2 CLI...")
    set_initdb_function(initialize_database)

    ctx = click.get_current_context()
    ctx.invoke(pulsemgr.callback, use_ipdb=use_ipdb)  # type: ignore


# @click.group(name="cmsfix2mgr")
# def cmsfix2mgr():
#    pass


# cmsfix2mgr.params.extend(pulsemgr.params)
# for cmd_name, cmd_obj in pulsemgr.commands.items():
#    cmsfix2mgr.add_command(cmd_obj, name=cmd_name)


# 3. Add your new commands here


@cmsfix2mgr.command(name="site-list")
async def site_list():
    click.echo("Listing sites...")

    async with get_dbhandler() as dbh:
        sites = await dbh.repo.Site.list()
        for site in sites:
            click.echo(f"- {site.fqdn} (Group: {await site.awaitable_attrs.group})")


@cmsfix2mgr.command(name="institution-list")
async def institution_list():
    click.echo("Listing user domains...")

    async with get_dbhandler() as dbh:
        institutions = await dbh.repo.institution.list()
        for institution in institutions:
            click.echo(f"- {institution.name}")


@cmsfix2mgr.command(name="institution-add")
async def institution_add():
    click.echo("Adding new institution...")


@cmsfix2mgr.command(name="project-list")
async def project_list():
    pass


@cmsfix2mgr.command(name="project-add")
async def project_add():
    pass


# EOF
