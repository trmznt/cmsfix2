from __future__ import annotations

import os
import uuid
from collections import deque
from typing import Any, Optional

import posixpath, time, datetime, difflib, yaml

from sqlalchemy import ForeignKey, Sequence, UniqueConstraint, types
from sqlalchemy.orm import (
    DynamicMapped,
    Mapped,
    mapped_column,
    relationship,
    object_session,
    deferred,
    backref,
)
from sqlalchemy.sql import func
from sqlalchemy.ext.orderinglist import ordering_list

from advanced_alchemy.types import JsonB


from litestar_pulse.lib import roles as r
from litestar_pulse.db.models.coremixins import IdentityUUIDv7UserAuditBase, RoleMixin
from litestar_pulse.db.models.account import User, Group
from litestar_pulse.db.models.enumkey import EnumKey, enumkey_proxy


# the models employ litestar_pulse's BaseMixIn to provide id, lastuser_id and stamp


class Site(IdentityUUIDv7UserAuditBase, RoleMixin):
    """this class manages sites"""

    __tablename__ = "sites"

    fqdn: Mapped[str] = mapped_column(
        types.String(128), nullable=False, index=True, server_default="*"
    )

    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    group: Mapped[Group] = relationship(Group, uselist=False, foreign_keys=[group_id])


class Node(IdentityUUIDv7UserAuditBase, RoleMixin):
    """this class manages all objects that have path and permission"""

    __tablename__ = "nodes"

    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), nullable=False)
    site: Mapped[Site] = relationship("Site", uselist=False)

    slug: Mapped[str] = mapped_column(types.String(128), nullable=False, index=True)
    path: Mapped[str] = mapped_column(
        types.String(1024), nullable=False, server_default=""
    )
    level: Mapped[int] = mapped_column(
        types.Integer, nullable=False, server_default="-1"
    )

    title: Mapped[str] = mapped_column(
        types.String(256), nullable=False, server_default=""
    )

    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("nodes.id"), nullable=True, index=True
    )
    parent: Mapped[Optional["Node"]] = relationship(
        "Node",
        remote_side="Node.id",
        backref=backref("children", cascade="all, delete-orphan"),
    )
    children: DynamicMapped["Node"] = relationship(
        "Node",
        cascade="all, delete-orphan",
        backref=backref("parent", remote_side="Node.id"),
        order_by="Node.ordering",
        lazy="dynamic",
        collection_class=ordering_list("ordering"),
    )

    ordering: Mapped[int] = mapped_column(types.Integer, nullable=False)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    user: Mapped[User] = relationship(User, uselist=False, foreign_keys=[user_id])

    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=False)
    group: Mapped[Group] = relationship(Group, uselist=False, foreign_keys=[group_id])

    create_time: Mapped[datetime.datetime] = mapped_column(
        types.DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    publish_time: Mapped[datetime.datetime] = mapped_column(
        types.DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expire_time: Mapped[Optional[datetime.datetime]] = mapped_column(
        types.DateTime(timezone=True), nullable=True
    )

    # state represent the workflow status, with global value of 0 being public
    # the meaning of the values depends on the workflow
    state: Mapped[int] = mapped_column(
        types.Integer, nullable=False, server_default="0"
    )

    # flags can be used to indicate special meta-information for the node
    # the lowest 16-bit may be interpreted freely by any viewer of each Node-subclass
    # the highest 16-bit is preserved for system

    flags: Mapped[int] = mapped_column(
        types.Integer, nullable=False, server_default="0"
    )

    # boolean to indicate whether this node will appear in the Content tab
    listed: Mapped[bool] = mapped_column(
        types.Boolean, nullable=False, server_default="1"
    )

    mimetype_id: Mapped[int] = mapped_column(ForeignKey("eks.id"), nullable=False)
    mimetype = enumkey_proxy("mimetype_id", "@MIMETYPE")

    json_code: Mapped[dict[str, Any]] = deferred(
        mapped_column(JsonB, nullable=False, server_default="{}")
    )
    # for more options on the above, see note at the end of this file

    polymorphic_type: Mapped[int] = mapped_column(
        types.Integer, nullable=False, server_default="0", index=True
    )

    __mapper_args__ = {"polymorphic_on": polymorphic_type, "polymorphic_identity": 0}
    __table_args__ = (
        UniqueConstraint("path", "site_id"),
        UniqueConstraint("parent_id", "ordering"),
    )

    __strict_container__ = None
    __mimetypes__ = None

    # flag options
    f_commentable = 1 << 15
    f_inmenu = 1 << 14

    def __init__(self, UUID=None, **kwargs):
        if not UUID:
            self.uuid = uuid.uuid1()
        else:
            self.uuid = UUID
        self._versioning = None
        self.flags = 0

        super().__init__(**kwargs)

    def clear(self):
        """this clear all child nodes and perform necessary cleanup"""

        session = object_session(self)
        if not session:
            raise RuntimeError("Node.clear() needs to be called within a session")

        for child in self.children:
            child.clear()
            session.delete(child)

    def generate_slug(self):
        """generate random slug based on time"""
        self.slug = str(time.time())

    def generate_path(self):
        if not self.slug:
            raise RuntimeError("Node slug needs to be initialized first!")
        parent_path = self.parent.path if self.parent else "/"
        if parent_path == "/":
            self.path = posixpath.normpath("/%s" % self.slug)
        else:
            self.path = posixpath.normpath("%s/%s" % (parent_path, self.slug))
        return self.path

    def render_title(self):
        return self.title

    def is_manageable(self, user):
        # check if user has ADMIN role or owner of this page
        if not user:
            return False
        if self.user == user or user.has_roles(r.SYSADM, r.DATAADM):
            return True
        # check if user is a member of the group and group is writable:
        if self.group.has_member(user):
            return True
        return False

    # Flags related functions

    def is_commentable(self):
        return self.flags & (1 << 15)

    def set_commentable(self, val=True):
        self.flags |= (1 if val else 0) << 15

    def is_inmenu(self):
        return self.flags & (1 << 14)

    def set_inmenu(self, val=True):
        self.flags |= (1 if val else 0) << 14

    def check_flags(self, flag):
        return self.flags & flag

    def set_flags(self, flag, val):
        self.flags = (self.flags | flag) if val is True else (self.flags & ~flag)

    def add(self, n):
        session = object_session(self)
        if not session:
            raise RuntimeError("Node.add() needs to be called within a session")
        if session != object_session(n):
            raise RuntimeError(
                "Node.add() needs to be called with nodes in the same session"
            )
        with session.no_autoflush:
            if not n.slug:
                n.generate_slug()
            n.site_id = self.site_id
            n.level = self.level + 1
            self.children.append(n)
            n.generate_path()
            n.ordering = -1
        session.flush()
        n.ordering = 19 * n.id
        return n

    @property
    def url(self):
        """remove the leading slash (/) for use with request.route_url"""
        return self.path[1:]

    def get_descendants(self):
        """perform preorder iterative traversal of all children"""
        stack = deque([])
        preorder = [self]
        stack.append(self)

        if self.children.count() == 0:
            return preorder

        while len(stack) > 0:
            flag = 0
            par = None
            if (stack[len(stack) - 1]).children.count() == 0:
                X = stack.pop()

            else:
                par = stack[len(stack) - 1]

            if par:
                for i in range(0, par.children.count()):
                    child = par.children[i]
                    if child not in preorder:
                        flag = 1
                        stack.append(child)
                        preorder.append(child)
                        break

            if flag == 0:
                stack.pop()

        return preorder

    @classmethod
    def container(cls, item_cls):
        global _containers_
        register_nodeclass(item_cls)
        try:
            _containers_[cls].append(item_cls)
        except KeyError:
            _containers_[cls] = [item_cls]
        return item_cls

    @classmethod
    def explicit_container(cls, item_cls):
        global _explicit_containers_
        register_nodeclass(item_cls)
        try:
            _explicit_containers_[cls].append(item_cls)
        except KeyError:
            _explicit_containers_[cls] = [item_cls]
        return item_cls

    @classmethod
    def inherited_container(cls, item_cls):
        global _inherited_containers_
        register_nodeclass(item_cls)
        try:
            _inherited_containers_[cls].append(item_cls)
        except KeyError:
            _inherited_containers_[cls] = [item_cls]
        return item_cls

    def get_item_classes(self):
        global _containers_, _inherited_containers_, _explicit_containers_
        if (
            hasattr(self, "__strict_container__")
            and self.__strict_container__ is not None
        ):
            return self.__strict_container__
        # raise RuntimeError
        if "strict_container" in self.json_code:
            classnames = self.json_code["strict_container"]
            classitems = (
                _containers_.get(self.__class__, [])
                + self.get_inherited_item_classes()
                + _explicit_containers_.get(self.__class__, [])
            )
            classitems_d = {}
            for classitem in classitems:
                classitems_d[classitem.__name__] = classitem
            return [classitems_d[n] for n in classnames if n in classitems_d]
        cls_set = _containers_.get(self.__class__, [])
        for c, l in _inherited_containers_.items():
            if issubclass(self.__class__, c):
                cls_set = cls_set + l
        return cls_set

    def get_inherited_item_classes(self):
        cls_set = []
        for c, l in _inherited_containers_.items():
            if issubclass(self.__class__, c):
                cls_set = cls_set + l
        return cls_set

    @classmethod
    def search(cls, text, site_id):
        raise NotImplementedError

    @classmethod
    def get_label(cls):
        return getattr(cls, "__label__", cls.__name__)

    def as_dict(self):
        return dict(
            _type_=type(self).__name__,
            id=self.id,
            site=self.site.fqdn,
            uuid=str(self.uuid),
            slug=self.slug,
            path=self.path,
            level=self.level,
            parent_url=self.parent.url if self.parent else "",
            ordering=self.ordering,
            user=self.user.get_login(),
            updated_by=(
                self.updated_by.get_login()
                if self.updated_by
                else self.user.get_login()
            ),
            updated_at=self.updated_at.isoformat() if self.updated_at else None,
            group=self.group.name,
            create_time=self.create_time,
            publish_time=self.publish_time,
            expire_time=self.expire_time,
            state=self.state,
            flags=self.flags,
            listed=self.listed,
            mimetype=self.mimetype,
            json_code=self.json_code,
            tags=[t.tag.key for t in self.tags],
        )

    def as_yaml(self):
        return yaml.safe_dump(self.as_dict(), default_flow_style=False)

    @classmethod
    def from_dict(cls, d, obj=None):
        if not obj:
            obj = cls()
        if "uuid" in d:
            obj.uuid = uuid.UUID(d["uuid"])
            assert d["uuid"] == str(obj.uuid)
        cerr(f"Created instance of [{obj.__class__.__name__}] with uuid: {obj.uuid}")
        obj.update(d)
        # update the low-level data
        # obj.user = None
        # obj.group = None
        return obj

    # export/import

    def dump(self, target_dir):
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
        with open(target_dir + "/_c.yaml", "w") as f:
            f.write(self.as_yaml())

    @classmethod
    def _load(cls, d, source_dir):

        # restore user & group
        dbh = get_dbhandler()
        d["site_id"] = dbh.get_site(d["site"]).id
        user = dbh.get_user(d["user"])
        if not user:
            cexit("ERR: user %s does not exist!" % d["user"])
        d["user_id"] = user.id
        d["lastuser"] = d.get("lastuser", d["user"])
        lastuser = dbh.get_user(d["lastuser"])
        if not lastuser:
            cexit("ERR: user %s does not exist!" % d["lastuser"])
        d["lastuser_id"] = lastuser.id
        group = dbh.get_group(d["group"])
        if not group:
            cexit("ERR: group %s does not exist!" % d["group"])
        d["group_id"] = group.id
        mimetype = dbh.get_ekey(d["mimetype"])
        d["mimetype_id"] = mimetype.id

        # modify tags to ids
        if "tags" in d:
            d["tags"] = [dbh.get_ekey(t).id for t in d["tags"]]

        # recreate node
        n = cls.from_dict(d)
        dbh.session().add(n)
        print(n)
        return n

    @staticmethod
    def load(source_dir):
        with open(source_dir + "/_c.yaml") as f:
            d = yaml.load(f.read())
        nodeclass = _nodeclasses_[d["_type_"]]
        print("NodeClass:", nodeclass)
        return nodeclass._load(d, source_dir)

    def ascendant(self, node):
        """check wheter self is an ascendant of node"""
        if self.level < node.level:
            return False
        if self.level == node.level:
            return True if self == node else False
        parent_node = self.parent
        while parent_node.level >= node.level:
            if parent_node == node:
                return True
            parent_node = self.parent
        return False

    def versioning(self):
        self._versioning = self.as_yaml().splitlines()

    def diff(self):
        curr_yaml = self.as_yaml().splitlines()
        # difflib between self._versioning and curr_yaml
        return difflib.context_diff(self._versioning, curr_yaml, n=1)

    def difflog(self):
        diff = "".join(self.diff())
        # create a difflog
        difflog_item = DiffLog()
        difflog_item.node = self
        difflog_item.diff = diff
        object_session(self).flush(difflog_item)
        return difflog_item

    def search_text(self):
        return ""

    def search_keywords(self):
        return ""

    def __repr__(self):
        return "<%s|%s|%s|%s>" % (
            self.__class__.__name__,
            self.id,
            self.path,
            self.title,
        )


class DiffLog(BaseMixIn, Base):

    __tablename__ = "difflogs"

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"), nullable=False)
    node: Mapped[Node] = relationship(
        Node,
        uselist=False,
        backref=backref("difflog", cascade="all, delete-orphan"),
    )

    diff: Mapped[str] = mapped_column(types.Text, nullable=False, server_default="")

    def __repr__(self):
        return "<DiffLog|%d|%s>" % (self.node_id, self.stamp)


class Workflow(BaseMixIn, Base):

    __tablename__ = "workflows"

    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"), nullable=False)
    node: Mapped[Node] = relationship(Node, uselist=False)

    state: Mapped[int] = mapped_column(
        types.Integer, nullable=False, server_default="0"
    )
    # state indicates the position in the workflow step
    # 0 - the final step, ie. published

    log: Mapped[str] = mapped_column(
        types.String(256), nullable=False, server_default=""
    )

    __table_args__ = (UniqueConstraint("node_id", "state"),)


class ACL(BaseMixIn, Base):

    __tablename__ = "xacls"

    node_id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id"), nullable=False, index=True
    )
    node: Mapped[Node] = relationship(Node, uselist=False)

    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    group_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("groups.id"), nullable=True
    )

    mode: Mapped[int] = mapped_column(types.Integer, nullable=False, server_default="0")

    __table_args__ = (
        UniqueConstraint("node_id", "user_id"),
        UniqueConstraint("node_id", "group_id"),
    )


class Tag(Base):

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(types.Integer, primary_key=True)

    node_id: Mapped[int] = mapped_column(
        ForeignKey("nodes.id"), nullable=False, index=True
    )
    node: Mapped[Node] = relationship(
        Node,
        uselist=False,
        backref=backref("tags", cascade="delete, delete-orphan"),
    )

    tag_id: Mapped[int] = mapped_column(
        ForeignKey("eks.id"), nullable=False, index=True
    )
    tag: Mapped[EK] = relationship(EK, uselist=False, foreign_keys=[tag_id])

    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))

    __table_args__ = (UniqueConstraint("node_id", "tag_id"),)

    @classmethod
    def sync_tags(cls, node_id, tag_keys, user_id=None, session=None):
        # synchronize node_id and tag_keys
        # tag_keys are eiither the actual, new tags or :id notation
        # eg. [ 'DNA', 'RNA', ':65', ':24']

        # check sanity
        assert type(node_id) == int

        tag_ids = []
        for t in tag_keys:
            if t[0] == ":":
                tag_ids.append(int(t[1:]))
            else:
                tag_ids.append(t)

        # check user_id first
        if not user_id:
            user_id = get_userid()

        if not session:
            session = get_dbhandler().session()

        tags = cls.query(session).filter(cls.node_id == node_id)
        in_sync = []
        for tag in tags:
            if tag.tag_id in tag_ids:
                in_sync.append(tag.tag_id)
            else:
                # remove this tag
                session.delete(tag)

        for tag_id in tag_ids:
            if tag_id in in_sync:
                continue
            cls.add_tag(node_id, tag_id, user_id, session)

    @classmethod
    def add_tag(cls, node_id, tag_id, user_id, session):
        # XXX: check if we need to create new tag, and set the owner
        if type(tag_id) == str:
            # check if we alreday have identical tag
            login = User.query(session).filter(User.id == user_id).one().login
            ek_tag = EK.search("@TAG", None, session)
            ekey = EK.search(tag_id, ek_tag, session)
            if ekey is None:
                # create new tag
                ekey = EK(key=tag_id, desc=login, parent=ek_tag)
                session.add(ekey)
                session.flush([ekey])
            tag_id = ekey.id

        assert type(tag_id) == int

        if not session:
            session = get_dbhandler().session()
        if type(node_id) == int:
            tag = cls(node_id=node_id, tag_id=tag_id, user_id=user_id)
        else:
            tag = cls(node=node_id, tag_id=tag_id, user_id=user_id)
        session.add(tag)

    @classmethod
    def remove_tag(cls, node_id, tag_id, user_id, session):
        tag = cls.query().filter(cls.node_id == node_id, cls.tag_id == tag_id).one()
        session.delete(tag)


class NodeRelationship(Base):

    __tablename__ = "noderelationships"

    id: Mapped[int] = mapped_column(
        types.Integer, Sequence("noderelationship_id", optional=True), primary_key=True
    )
    node1_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"), nullable=False)
    node2_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"), nullable=False)
    text: Mapped[str] = mapped_column(
        types.String(64), nullable=False, server_default=""
    )
    ordering: Mapped[int] = mapped_column(
        types.Integer, nullable=False, server_default="0"
    )

    __table_args__ = (UniqueConstraint("node1_id", "node2_id"), {})

    node1: Mapped[Node] = relationship(
        Node,
        uselist=False,
        foreign_keys=[node1_id],
        backref=backref("noderel1", cascade="all,delete,delete-orphan"),
    )
    node2: Mapped[Node] = relationship(
        Node,
        uselist=False,
        foreign_keys=[node2_id],
        backref=backref("noderel2", cascade="all,delete,delete-orphan"),
    )

    @classmethod
    def create(cls, node1, node2, text=""):
        r = cls(node1_id=node1.id, node2_id=node2.id, text=text)
        s = object_session(node1)
        s.add(r)
        s.flush([r])
        r.ordering = r.id * 19
        return r

    @classmethod
    def gets(cls, ids, session):
        return cls.query(session).filter(cls.id.in_(ids))

    @classmethod
    def node_relationship(cls, params):
        return relationship()


# container related
# the structure for below variabels is:
# d[cls] = [ cls1, cls2, ... ]

_containers_ = {}
_inherited_containers_ = {}
_explicit_containers_ = {}


def self_container(item_cls):
    global _containers_
    register_nodeclass(item_cls)
    try:
        _containers_[item_cls].append(item_cls)
    except KeyError:
        _containers_[item_cls] = [item_cls]
    return item_cls


_nodeclasses_ = {}


def register_nodeclass(cls):
    global _nodeclasses_
    cerr("Registering [%s]" % cls.__name__)
    if cls.__name__ not in _nodeclasses_:
        _nodeclasses_[cls.__name__] = cls
    elif _nodeclasses_[cls.__name__] != cls:
        raise RuntimeError("inconsistent class %s" % cls.__name__)


__NOTE__ = """

json_code can be used to further control a node.
Below are options used in json_code:

strict_containers: [ ]


"""

# EOF
