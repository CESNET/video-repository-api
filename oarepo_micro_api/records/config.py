# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 CERN.
#
# OARepo Micro API is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""Default configuration."""

from __future__ import absolute_import, print_function

from elasticsearch_dsl import Q
from invenio_indexer.api import RecordIndexer
from invenio_records_rest.facets import terms_filter
from invenio_records_rest.query import default_search_factory
from invenio_records_rest.utils import allow_all, check_elasticsearch

from oarepo_micro_api.records.api import Record


def _(x):
    """Identity function for string extraction."""
    return x


def nested_filter(prefix, field, field_query=None, nested_query='terms'):
    """Create a term filter.
    :param prefix: Field path prefix
    :param field: Field name.
    :param field_query Field query function
    :param nested_query Nested query name
    :returns: Function that returns the Terms query.
    """
    field = prefix + '.' + field

    def inner(values):
        if field_query:
            query = field_query(field)(values)
        else:
            query = Q(nested_query, **{field: values})
        return Q('nested', path=prefix, query=query)

    return inner


def language_aware_match_filter(field):
    return nested_filter(field, 'value', nested_query='match')


def search_title(qstr=None):
    if qstr:
        return language_aware_match_filter('title')(qstr)
    return Q()


def search_factory(*args, **kwargs):
    return default_search_factory(*args, query_parser=search_title, **kwargs)


FILTERS = {
    'title': language_aware_match_filter('title'),
    'creator': terms_filter('creator.keyword'),
    'lang': terms_filter('title.lang.keyword')
}

RECORDS_REST_ENDPOINTS = {
    'recid': dict(
        pid_type='recid',
        pid_minter='recid',
        pid_fetcher='recid',
        default_endpoint_prefix=True,
        record_class=Record,
        indexer_class=RecordIndexer,
        search_factory_imp=search_factory,
        search_index='records-record-v1.0.0',
        search_type=None,
        record_serializers={
            'application/json': ('oarepo_micro_api.records.serializers'
                                 ':json_v1_response'),
        },
        search_serializers={
            'application/json': ('oarepo_micro_api.records.serializers'
                                 ':json_v1_search'),
        },
        record_loaders={
            'application/json': ('oarepo_micro_api.records.loaders'
                                 ':json_v1'),
        },
        list_route='/records/',
        item_route='/records/<pid(recid,'
                   'record_class="oarepo_micro_api.records.api.Record")'
                   ':pid_value>',
        default_media_type='application/json',
        max_result_window=10000,
        error_handlers=dict(),
        create_permission_factory_imp=allow_all,
        read_permission_factory_imp=check_elasticsearch,
        update_permission_factory_imp=allow_all,
        delete_permission_factory_imp=allow_all,
        list_permission_factory_imp=allow_all,
        links_factory_imp='invenio_records_files.'
                          'links:default_record_files_links_factory',
    ),
}
"""REST API for oarepo_micro_api."""

INVENIO_OAREPO_UI_COLLECTIONS = {
    "records": {
        "title": {
            "cs-cz": "Ukázkové záznamy v repozitáři",
            "en-us": "Demo Repository Records"
        },
        "description": {
            "cs-cz": """
                Kolekce ukázkových záznamů odpovídajících DCObject metadatovému schematu.
                """,
            "en-us": """
                A collection of a Demo Records that adhere to the DCObject metadata schema.
                """
        },
        "rest": "/api/records/",
        "facet_filters": list(FILTERS.keys())
    }
}
""" OARepo UI collections API configuration. """

RECORDS_UI_ENDPOINTS = dict(
    recid=dict(
        pid_type='recid',
        route='/records/<pid_value>',
        template='records/record.html',
        record_class='invenio_records_files.api:Record',
    ),
    recid_previewer=dict(
        pid_type='recid',
        route='/records/<pid_value>/preview/<path:filename>',
        view_imp='invenio_previewer.views.preview',
        record_class='invenio_records_files.api:Record',
    ),
    recid_files=dict(
        pid_type='recid',
        route='/records/<pid_value>/files/<path:filename>',
        view_imp='invenio_records_files.utils.file_download_ui',
        record_class='invenio_records_files.api:Record',
    ),
)
"""Records UI for oarepo_micro_api."""

PIDSTORE_RECID_FIELD = 'pid'

OAREPO_API_ENDPOINTS_ENABLED = True
"""Enable/disable automatic endpoint registration."""


def term_facet(field, order='desc', size=100):
    return {
        'terms': {
            'field': field,
            'size': size,
            "order": {"_key": order}
        },
    }


RECORDS_REST_FACETS = {
    'records-record-v1.0.0': {
        'aggs': {
            'creator': term_facet('creator.keyword'),
            'lang': term_facet('title.lang.keyword'),
        },
        'post_filters': FILTERS,
        'filters': FILTERS
    }
}
"""Introduce searching facets."""

RECORDS_REST_SORT_OPTIONS = dict(
    records=dict(
        bestmatch=dict(
            title=_('Best match'),
            fields=['_score'],
            default_order='desc',
            order=1,
        ),
        mostrecent=dict(
            title=_('Most recent'),
            fields=['-_created'],
            default_order='asc',
            order=2,
        ),
    )
)
"""Setup sorting options."""

RECORDS_REST_DEFAULT_SORT = dict(
    records=dict(
        query='bestmatch',
        noquery='mostrecent',
    )
)
"""Set default sorting options."""

RECORDS_FILES_REST_ENDPOINTS = {
    'RECORDS_REST_ENDPOINTS': {
        'recid': '/files'
    },
}
"""Records files integration."""

FILES_REST_PERMISSION_FACTORY = \
    'oarepo_micro_api.records.permissions:files_permission_factory'
"""Files-REST permissions factory."""
