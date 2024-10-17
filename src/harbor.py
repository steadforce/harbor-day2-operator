"""Harbor Day 2 Operator

This harbor operator makes it possible to synchronize
different types of settings to a harbor instance.
Instead of making changes by hand (clickops), this operator
enables the automatic synchronization of harbor settings from files.

The Harbor API of your instance can be found at:
your-harbor-origin/devcenter-api-2.0
"""


import asyncio
from enum import Enum


from harborapi import HarborAsyncClient
from harborapi.exceptions import NotFound, Unauthorized, Conflict, BadRequest
from harborapi.models import (
    Robot,
    Configurations,
    Registry,
    WebhookPolicy,
    Project,
    ProjectMemberEntity,
    Schedule,
    RetentionPolicy
)
import argparse
import json
import os
from time import sleep

from utils import wait_until_healthy, sync_admin_password
from configuration import sync_harbor_configuration
from registries import sync_registries
from projects import sync_projects
from project_members import sync_project_members
from robot_accounts import sync_robot_accounts
from webhooks import sync_webhooks
from purge_job_schedule import sync_purge_job_schedule
from garbage_collection_schedule import sync_garbage_collection_schedule


class ProjectRole(Enum):
    ADMIN = 1
    DEVELOPER = 2
    GUEST = 3
    MAINTAINER = 4


admin_username = os.environ.get("ADMIN_USERNAME", "admin")
old_admin_password = os.environ.get("ADMIN_PASSWORD_OLD")
new_admin_password = os.environ.get("ADMIN_PASSWORD_NEW")
api_url = os.environ.get("HARBOR_API_URL")
config_folder_path = os.environ.get("CONFIG_FOLDER_PATH")
robot_name_prefix = os.environ.get("ROBOT_NAME_PREFIX")
oidc_client_secret = os.environ.get("OIDC_STATIC_CLIENT_TOKEN")
oidc_endpoint = os.environ.get("OIDC_ENDPOINT")


async def main() -> None:
    parse_args()

    global client
    client = HarborAsyncClient(
        url=api_url,
        username=admin_username,
        secret=new_admin_password,
        timeout=100,
        verify=False,
    )

    # Wait for healthy harbor
    print("WAITING FOR HEALTHY HARBOR")
    await wait_until_healthy()
    print("")

    # Update admin password
    print("UPDATE ADMIN PASSWORD")
    await sync_admin_password()
    print("")

    if check_file_exists("configurations.json"):
        await sync_harbor_configuration()

    if check_file_exists("registries.json"):
        await sync_registries()

    if check_file_exists("projects.json"):
        await sync_projects()

    if check_file_exists("project-members.json"):
        await sync_project_members()

    if check_file_exists("robot-accounts.json"):
        await sync_robot_accounts()

    if check_file_exists("webhooks.json"):
        await sync_webhooks()

    if check_file_exists("purge-job-schedule.json"):
        await sync_purge_job_schedule()

    if check_file_exists("garbage-collection-schedule.json"):
        await sync_garbage_collection_schedule()

    if check_file_exists("retention-policies.json"):
        await sync_retention_policies()


def parse_args():
    parser = argparse.ArgumentParser(
        description="""Harbor Day 2 configurator to sync harbor configs""",
    )
    args = parser.parse_args()
    return args


asyncio.run(main())
