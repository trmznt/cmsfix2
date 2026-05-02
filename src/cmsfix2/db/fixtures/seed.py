from ...lib.roles import *

GROUPS = [
    # (group_name, [assigned_enumkeys for roles])
    ("Editor", [EDITOR]),
    ("Reviewer", [REVIEWER]),
    ("SiteManager", [SITE_MANAGE, SITE_MODIFY]),
]

ENUMKEYS = [
    # (enumkey, description)
    (
        "@ROLES",
        None,
        [
            (SITE_MANAGE, "Can manage site settings"),
            (SITE_MODIFY, "Can modify site content"),
            (EDITOR, "Can edit content"),
            (REVIEWER, "Can review content"),
        ],
    )
]

SITES = [
    # (fqdn, groups with access to the site)
    ("*", "SiteManager"),
]

NODES = [
    # (type, site, slug, parent_slug, title, user, group)
    "Node", "*", "/", None, "root", "sysadm", "SiteManager" 
]
# EOF
