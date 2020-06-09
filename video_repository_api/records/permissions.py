# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 CERN.
#
# OARepo Micro API is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Permissions for OARepo Micro API."""
from elasticsearch_dsl import Q
from flask_login import current_user
from flask_principal import UserNeed, RoleNeed
from invenio_access import Permission, authenticated_user, any_user


def _get_owners(record):
    owners = record.get('owners')
    try:
        owners.remove(-1)
    except ValueError:
        pass
    return owners


def authenticated_permission_factory(record=None):
    return Permission(authenticated_user)


def admin_permission_factory(obj, action=None):
    """Permissions factory for buckets."""
    return Permission(RoleNeed('admin'))


def owner_permission_factory(record=None):
    """Permissions factory for record owners."""
    # TODO: adapt for more owners
    owners = _get_owners(record)
    if len(owners) > 0:
        return Permission(UserNeed(int(owners[0])))
    return Permission(UserNeed(-1))


def detail_permission_factory(record=None):
    """Permissions factory for record detail."""
    # TODO: adapt for more owners
    owners = _get_owners(record)
    if len(owners) > 0:
        return Permission(UserNeed(int(owners[0])))
    return Permission(any_user)


def owner_permission_filter(owned_only=False):
    """Search only in owned or system records."""
    ids = [] if owned_only else [-1]
    cuid = current_user.get_id()
    if cuid:
        ids.append(cuid)
    return Q('terms', owners=ids)
