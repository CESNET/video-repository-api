# -*- coding: utf-8 -*-
#
# Copyright (C) 2018-2020 CERN.
#
# OARepo Micro API is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CLI for Invenio App ILS."""
import json
import random

import click
import redis
from flask.cli import with_appcontext
from invenio_accounts.models import User
from invenio_app.factory import create_api
from invenio_db import db
from invenio_indexer.api import RecordIndexer
from invenio_pidstore.models import PIDStatus, PersistentIdentifier
from invenio_pidstore.providers.recordid_v2 import RecordIdProviderV2
from invenio_search import current_search, current_search_client
from invenio_userprofiles import UserProfile

from video_repository_api.records.api import Record
from video_repository_api.records.constants import ACL_PREFERRED_SCHEMA


def create_pid():
    """Create a new persistent identifier."""
    return RecordIdProviderV2.create().pid.pid_value


def minter(pid_type, pid_field, record):
    """Mint the given PID for the given record."""
    if pid_field not in record.keys():
        record[pid_field] = create_pid()

    pid = PersistentIdentifier.get(
        pid_type="recid",
        pid_value=record[pid_field]
    )
    pid.status = PIDStatus.REGISTERED
    pid.object_type = "rec"
    pid.object_uuid = record.id
    pid.pid_type = pid_type


def create_userprofile_for(email, username, full_name):
    """Create a user profile."""
    user = User.query.filter_by(email=email).one_or_none()
    if user:
        profile = UserProfile(user_id=int(user.get_id()))
        profile.username = username
        profile.full_name = full_name
        db.session.add(profile)
        db.session.commit()


def random_lang():
    """Create a random language."""
    return random.choice(['en', 'cs', 'de', 'fr', 'es'])


class Holder(object):
    """Holds generated data."""

    def __init__(self):
        """Constructor."""
        self.items = {"objs": [], "total": 0}

    def pids(self, collection, pid_field):
        """Get a list of PIDs for a collection."""
        return [obj[pid_field] for obj in getattr(self, collection)["objs"]]


class Generator(object):
    """Generator."""

    def __init__(self, holder):
        """Constructor."""
        self.holder = holder
        # self.minter = minter

    def _persist(self, pid_type, pid_field, record):
        """Mint PID and store in the db."""
        minter(pid_type, pid_field, record)
        record.commit()
        return record


class DataLoader(Generator):
    """Demo Data Loader."""

    def load(self, file):
        """Load records from file."""
        with open(file, 'r') as source:
            sdata = source.read()

        objs = json.loads(sdata)

        self.holder.items["objs"] = objs
        self.holder.items["total"] = len(objs)

    def persist(self):
        """Persist."""
        recs = []
        for obj in self.holder.items["objs"]:
            # Set System owner for each record
            obj['owners'] = [-1]
            rec = self._persist("recid", "pid", Record.create(obj))
            recs.append(rec)
        db.session.commit()
        return recs


@click.group()
def demo():
    """Demo data CLI."""


@demo.command()
@click.argument('datafile', default='./assets/data/demo.json')
@with_appcontext
def data(datafile):
    """Insert demo data."""
    click.secho("Importing demo data from {}".format(datafile), fg="yellow")

    indexer = RecordIndexer()
    holder = Holder()

    loader = DataLoader(holder)
    loader.load(datafile)
    rec_items = loader.persist()
    for rec in rec_items:
        # TODO: bulk index when we have the queue in k8s deployment
        indexer.index(rec)

    current_search.flush_and_refresh(index="*")


@click.command()
@click.argument('admin_password')
@click.option(
    "--recreate-db",
    is_flag=True,
    help="Recreating DB."
)
@click.option(
    "--drop-taxonomies",
    is_flag=True,
    help="Drop taxonomy data."
)
@click.option(
    "--skip-demo-data",
    is_flag=True,
    help="Skip creating demo data."
)
@click.option(
    "--skip-taxonomy-import",
    is_flag=True,
    help="Skip import of taxonomy data."
)
@click.option(
    "--taxonomies",
    help="Path to a directory with taxonomy files",
    default="./assets/taxonomy"
)
@click.option(
    "--skip-file-location",
    is_flag=True,
    help="Skip creating file location."
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Verbose output."
)
@with_appcontext
def setup(admin_password, recreate_db, skip_demo_data,
          skip_file_location, drop_taxonomies,
          skip_taxonomy_import, verbose, taxonomies='./assets/taxonomy'):
    """OARepo setup command."""
    from flask import current_app
    from invenio_base.app import create_cli

    click.secho("oarepo setup started...", fg="blue")

    # Clean redis
    redis.StrictRedis.from_url(
        current_app.config["CACHE_REDIS_URL"]
    ).flushall()
    click.secho("redis cache cleared...", fg="red")

    cli = create_cli()

    # Important: force API app on CLI context for proper URL generation
    cli.create_app = create_api
    runner = create_api().test_cli_runner()

    def run_command(command, catch_exceptions=False):
        click.secho("oarepo {}...".format(command), fg="green")
        res = runner.invoke(cli, command, catch_exceptions=catch_exceptions)
        if verbose:
            click.secho(res.output)

    # Print all routes considered for URL generation
    run_command('routes')

    # Remove and create db and indexes
    if recreate_db:
        run_command("db destroy --yes-i-know", catch_exceptions=True)
        run_command("db init")
    else:
        run_command("db drop --yes-i-know")
    run_command("db create")
    run_command("index destroy --force --yes-i-know")
    run_command("index init --force")
    run_command("index queue init purge")

    # Create roles to restrict access
    run_command("roles create admin")

    # Create users
    run_command(
        "users create admin@oarepo.org -a --password={}".format(admin_password)
    )  # ID 1
    create_userprofile_for("admin@oarepo.org", "admin", "OArepo Administrator")

    # Assign roles
    run_command("roles add admin@oarepo.org admin")

    # Assign actions
    run_command("access allow superuser-access role admin")

    # Create files location
    if not skip_file_location:
        run_command("files location --default oarepo /tmp/oarepo")

    # Create ACLs index for preferred SCHEMA
    run_command("invenio invenio_explicit_acls prepare {}".format(ACL_PREFERRED_SCHEMA))

    # Drop taxonomy data
    if drop_taxonomies:
        taxo_list = runner.invoke(cli, 'taxonomies list', catch_exceptions=False)
        click.secho("oarepo dropping existing taxonomies {}".format(taxo_list.output), fg="yellow")
        for tax in [t for t in taxo_list.output.splitlines() if t[0] not in [' ', '*']]:
            click.secho("oarepo deleting taxonomy {}".format(tax), fg="yellow")
            run_command('taxonomies delete {}'.format(tax))

    # Import taxonomies
    if not skip_taxonomy_import:
        import os
        click.secho("oarepo importing taxonomies from {}".format(taxonomies), fg="green")
        for tax_file in os.listdir(taxonomies):
            if tax_file.endswith('xlsx'):
                tax_path = os.path.join(taxonomies, tax_file)
                click.secho("oarepo importing taxonomy {}".format(tax_path), fg="green")
                if tax_file.startswith('event'):
                    run_command('taxonomies import {} --str web --str organizer --str startDate --str endDate --bool '
                                'selectable --drop'.format(tax_path))
                elif tax_file.startswith('format'):
                    run_command('taxonomies import {} --str resolution --str spec --bool selectable --drop'
                                .format(tax_path))

        click.secho("oarepo setting all-read permission on taxonomies", fg="green")
        run_command('taxonomies all-read')
        # TODO: what about taxonomy modify?

        run_command('demo data')

    click.secho("oarepo setup finished successfully", fg="blue")


@demo.command('reindex')
@click.option(
    '--only',
    help='Index only this item')
@with_appcontext
@click.pass_context
def demo_reindex(only=None):
    with create_api().app_context():
        def reindex_pid(pid_type):
            for pid in PersistentIdentifier.query.filter_by(pid_type=pid_type, object_type='rec'):
                record = Record.get_record(pid.object_uuid)
                if only and str(record.id) != only:
                    continue
                try:
                    RecordIndexer().index(record)
                except:
                    with open('/tmp/indexing-error.json', 'w') as f:
                       print(json.dumps(record.dumps(), indent=4, ensure_ascii=False), file=f)
                    raise
            current_search_client.indices.flush()
        reindex_pid('recid')
