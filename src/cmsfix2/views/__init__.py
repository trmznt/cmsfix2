from __future__ import annotations

from typing import Any, Type

# this module provides registration of Node subviews and form models.


__subviews__ = dict()
__form_models__ = dict()


def register_subview(model: type[Any], view: type[Any]) -> None:
    global __subviews__
    __subviews__[model] = view


def register_form_model(model: type[Any], form_model: type[Any]) -> None:
    global __form_models__
    __form_models__[model] = form_model


def get_subview(model: type[Any]) -> Type[Any] | None:
    return __subviews__.get(model)


def get_form_model(model: type[Any]) -> Type[Any] | None:
    """ """
    return __form_models__.get(model)


# EOF
