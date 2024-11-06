"""Harbor Day 2 Operator

This harbor operator makes it possible to synchronize
different types of settings to a harbor instance.
Instead of making changes by hand (clickops), this operator
enables the automatic synchronization of harbor settings from files.

The Harbor API of your instance can be found at:
your-harbor-origin/devcenter-api-2.0
"""


from harborapi import HarborAsyncClient
import argparse
import os
import asyncio

from utils import wait_until_healthy, sync_admin_password, check_file_exists
from configuration import sync_harbor_configuration
from registries import sync_registries
from projects import sync_projects
from project_members import sync_project_members
from robot_accounts import sync_robot_accounts
from webhooks import sync_webhooks
from purge_job_schedule import sync_purge_job_schedule
from garbage_collection_schedule import sync_garbage_collection_schedule
from retention_policies import sync_retention_policies


admin_username = os.environ.get("ADMIN_USERNAME", "admin")
new_admin_password = os.environ.get("ADMIN_PASSWORD_NEW")
api_url = os.environ.get("HARBOR_API_URL")
config_folder_path = os.environ.get("CONFIG_FOLDER_PATH")


async def main() -> None:
    parse_args()

    client = HarborAsyncClient(
        url=api_url,
        username=admin_username,
        secret=new_admin_password,
        timeout=100,
        verify=False,
    )

    # Wait for healthy harbor
    print("WAITING FOR HEALTHY HARBOR")
    await wait_until_healthy(client)
    print("")

    # Update admin password
    print("UPDATE ADMIN PASSWORD")
    await sync_admin_password(client)
    print("")

    path = config_folder_path + "/configurations.json"
    if check_file_exists(path):
        await sync_harbor_configuration(client, path)

    path = config_folder_path + "/registries.json"
    if check_file_exists(path):
        await sync_registries(client, path)

    path = config_folder_path + "/projects.json"
    if check_file_exists(path):
        await sync_projects(client, path)

    path = config_folder_path + "/project-members.json"
    if check_file_exists(path):
        await sync_project_members(client, path)

    path = config_folder_path + "/robot-accounts.json"
    if check_file_exists(path):
        await sync_robot_accounts(client, path)

    path = config_folder_path + "/webhooks.json"
    if check_file_exists(path):
        await sync_webhooks(client, path)

    path = config_folder_path + "/purge-job-schedule.json"
    if check_file_exists(path):
        await sync_purge_job_schedule(client, path)

    path = config_folder_path + "/garbage-collection-schedule.json"
    if check_file_exists(path):
        await sync_garbage_collection_schedule(client, path)

    path = config_folder_path + "/retention-policies.json"
    if check_file_exists(path):
        await sync_retention_policies(client, path)


def parse_args():
    parser = argparse.ArgumentParser(
        description="""Harbor Day 2 configurator to sync harbor configs""",
    )
    args = parser.parse_args()
    return args


asyncio.run(main())
