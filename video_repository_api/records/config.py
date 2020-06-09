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
from invenio_records_rest.utils import allow_all
from invenio_search import RecordsSearch
from invenio_search.api import DefaultFilter

from video_repository_api.records.api import Record
from video_repository_api.records.facets import term_facet, title_lang_facet, taxonomy_facet
from video_repository_api.records.filters import language_aware_match_filter, nested_terms_filter, owned_filter, \
    language_aware_terms_filter
from video_repository_api.records.permissions import authenticated_permission_factory, admin_permission_factory, \
    owner_permission_filter, owner_permission_factory, detail_permission_factory


def _(x):
    """Identity function for string extraction."""
    return x


RECORDS_SEARCH_INDEX = 'records-record-v1.0.0'


def search_title(qstr=None):
    if qstr:
        return language_aware_match_filter('title')(qstr)
    return Q()


class FilteredRecordsSearch(RecordsSearch):
    class Meta:
        index = RECORDS_SEARCH_INDEX
        doc_types = None
        default_filter = DefaultFilter(owner_permission_filter)


def search_factory(*args, **kwargs):
    return default_search_factory(
        *args,
        query_parser=search_title,
        **kwargs)


FILTERS = {
    'title': language_aware_match_filter('title'),
    'creator': terms_filter('creator.keyword'),
    'owned': owned_filter('owners'),
    'difficulty': terms_filter('difficulty'),
    'license': terms_filter('license.keyword'),
    'event.title.value.keyword': language_aware_terms_filter('event.title'),
    'formats.title.value.keyword': language_aware_terms_filter('formats.title'),
    'title.lang': nested_terms_filter('title', 'lang', lambda field: terms_filter(f'{field}')),
}

RECORDS_REST_ENDPOINTS = {
    'recid': dict(
        pid_type='recid',
        pid_minter='recid',
        pid_fetcher='recid',
        default_endpoint_prefix=True,
        record_class=Record,
        indexer_class=RecordIndexer,
        search_class=FilteredRecordsSearch,
        search_factory_imp=search_factory,
        search_index=RECORDS_SEARCH_INDEX,
        search_type=None,
        record_serializers={
            'application/json': ('video_repository_api.records.serializers'
                                 ':json_v1_response'),
            'text/x-bibliography': ('video_repository_api.records.serializers'
                                    ':citeproc_v1_response'),
        },
        search_serializers={
            'application/json': ('video_repository_api.records.serializers'
                                 ':json_v1_search'),
        },
        record_loaders={
            'application/json': ('video_repository_api.records.loaders'
                                 ':json_v1'),
            'application/json-patch+json': ('invenio_records_rest.loaders'
                                            ':json_patch_loader'),
        },
        list_route='/records/',
        item_route='/records/<pid(recid,'
                   'record_class="video_repository_api.records.api.Record")'
                   ':pid_value>',
        default_media_type='application/json',
        max_result_window=10000,
        error_handlers=dict(),
        create_permission_factory_imp=authenticated_permission_factory,
        read_permission_factory_imp=detail_permission_factory,
        update_permission_factory_imp=owner_permission_factory,
        delete_permission_factory_imp=admin_permission_factory,
        list_permission_factory_imp=allow_all,
        links_factory_imp='invenio_records_files.'
                          'links:default_record_files_links_factory',
    ),
}
"""REST API for video_repository_api."""

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
"""Records UI for video_repository_api."""

PIDSTORE_RECID_FIELD = 'pid'

OAREPO_API_ENDPOINTS_ENABLED = True
"""Enable/disable automatic endpoint registration."""

RECORDS_REST_FACETS = {
    RECORDS_SEARCH_INDEX: {
        'aggs': {
            'creator': term_facet('creator.keyword'),
            'difficulty': term_facet('difficulty'),
            'event': taxonomy_facet('event'),
            'license': term_facet('license'),
            'formats': taxonomy_facet('formats'),
            'lang': title_lang_facet(),
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
    'video_repository_api.records.permissions:admin_permission_factory'
"""Files-REST permissions factory."""
