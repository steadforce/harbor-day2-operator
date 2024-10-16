import asyncio
from enum import Enum

# API calls to configure harbor:
# See Harbor api: https://harbor.dev.k8s01.steadforce.com/devcenter-api-2.0
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

import sync_harbor_configuration from configuration
import sync_registries from registries
import sync_projects from projects
import sync_project_members from project_members
import sync_robot_accounts from robot_accounts
import sync_webhooks from webhooks
import sync_purge_job_schedule from purge_job_schedule
import sync_garbage_collection_schedule from garbage_collection_schedule


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

    sync_harbor_configuration()

    sync_registries()

    sync_projects()

    sync_project_members()

    sync_robot_accounts()

    sync_webhooks()

    sync_purge_job_schedule()

    sync_garbage_collection_schedule()


async def wait_until_healthy() -> None:
    while True:
        health = await client.health_check()
        if health.status == "healthy":
            print("- Harbor is healthy")
            break
        print("- Waiting for harbor to become healthy...")
        sleep(5)


async def update_password() -> None:
    try:
        print("Updating password")
        old_password_client = HarborAsyncClient(
            url=api_url,
            username=admin_username,
            secret=old_admin_password,
            timeout=10,
            verify=False,
        )
        admin = await old_password_client.get_current_user()
        await old_password_client.set_user_password(
            user_id=admin.user_id,
            old_password=old_admin_password,
            new_password=new_admin_password,
        )
        print("- Updated admin password")
    except Unauthorized:
        print(
            "  => ERROR: Unable to change the admin password."
            "  Neither the old nor the new password are correct."
        )


async def sync_admin_password() -> None:
    try:
        await client.get_current_user()
    except Unauthorized:
        await update_password()


def get_member_id(members: [ProjectMemberEntity], username: str) -> int | None:
    """Returns member id of username or None if username is not in members"""
    for member in members:
        if member.entity_name == username:
            return member.id
    return None


def parse_args():
    parser = argparse.ArgumentParser(
        description="""Harbor Day 2 configurator to sync harbor configs""",
    )
    args = parser.parse_args()
    return args


asyncio.run(main())
