# -*- coding: utf-8 -*-
#
# Copyright (C) 2020 CERN.
#
# OARepo Micro API is free software; you can redistribute it and/or modify it under
# the terms of the MIT License; see LICENSE file for more details.

"""JSON Schemas."""

from __future__ import absolute_import, print_function

from flask_login import current_user
from flask_taxonomies.marshmallow import TaxonomySchemaV1
from invenio_jsonschemas import current_jsonschemas
from invenio_oarepo_dc.marshmallow import DCObjectSchemaV1Mixin
from invenio_oarepo_invenio_model.marshmallow import InvenioRecordMetadataSchemaV1Mixin
from invenio_oarepo_multilingual.marshmallow import MultilingualStringSchemaV1
from invenio_rest.serializer import BaseSchema as Schema
from invenio_records_rest.schemas import StrictKeysMixin
from invenio_records_rest.schemas.fields import GenFunction, \
    PersistentIdentifier, SanitizedUnicode
from marshmallow import fields, missing, INCLUDE, pre_load

from video_repository_api.records.api import Record
from video_repository_api.records.constants import ACL_ALLOWED_SCHEMAS, ACL_PREFERRED_SCHEMA


def bucket_from_context(_, context):
    """Get the record's bucket from context."""
    record = (context or {}).get('record', {})
    return record.get('_bucket', missing)


def files_from_context(_, context):
    """Get the record's files from context."""
    record = (context or {}).get('record', {})
    return record.get('_files', missing)


def schema_from_context(_, context):
    """Get the record's schema from context."""
    record = (context or {}).get('record', {})
    return record.get(
        "_schema",
        current_jsonschemas.path_to_url(Record._schema)
    )


class CitationSchemaV1(Schema):
    id = fields.Integer(attribute='pid.pid_value')
    type = fields.Method('get_type')
    title = fields.Str(attribute='metadata.title')
    abstract = fields.Str(attribute='metadata.description')
    author = fields.Str(attribute='metadata.creator')
    contributors = fields.Str(attribute='metadata.contributor')

    def get_type(self, obj):
        return 'article'


class EventSchemaV1(TaxonomySchemaV1):
    web = fields.URL()
    organizer = SanitizedUnicode()
    startDate = SanitizedUnicode()
    endDate = SanitizedUnicode()
    selectable = fields.Boolean(default=True)


class FormatSchemaV1(TaxonomySchemaV1):
    resolution = SanitizedUnicode()
    spec = SanitizedUnicode()
    selectable = fields.Boolean(default=True)


class MetadataSchemaV1(InvenioRecordMetadataSchemaV1Mixin,
                       DCObjectSchemaV1Mixin,
                       StrictKeysMixin):
    """Schema for the record metadata."""
    ALLOWED_SCHEMAS = ACL_ALLOWED_SCHEMAS
    PREFERRED_SCHEMA = ACL_PREFERRED_SCHEMA

    owners = fields.List(fields.Int(), dump_only=True)
    abstract = MultilingualStringSchemaV1(required=True)
    description = MultilingualStringSchemaV1(required=True)
    contributors = SanitizedUnicode(required=False)
    event = fields.Nested(EventSchemaV1(), required=False)
    difficulty = SanitizedUnicode(required=True)
    license = SanitizedUnicode(required=True)
    formats = fields.Nested(FormatSchemaV1(many=True), many=True, required=False)
    source = fields.URL()

    @pre_load
    def set_owners(self, in_data, **kwargs):
        if current_user.is_authenticated:
            in_data['owners'] = [current_user.get_id()]
        return in_data

    class Meta:
        unknown = INCLUDE


class RecordSchemaV1(StrictKeysMixin):
    """Record schema."""
    metadata = fields.Nested(MetadataSchemaV1)
    created = fields.Str(dump_only=True)
    revision = fields.Integer(dump_only=True)
    updated = fields.Str(dump_only=True)
    links = fields.Dict(dump_only=True)
    id = PersistentIdentifier()
    files = GenFunction(
        serialize=files_from_context, deserialize=files_from_context)
