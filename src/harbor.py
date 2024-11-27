"""Harbor Day 2 Operator

This harbor operator makes it possible to synchronize
different types of settings to a harbor instance.
Instead of making changes by hand (clickops), this operator
enables the automatic synchronization of harbor settings from files.

The Harbor API of your instance can be found at:
your-harbor-origin/devcenter-api-2.0
"""


import argparse
import os
import asyncio
import logging

from harborapi import HarborAsyncClient
from pythonjsonlogger import jsonlogger
from utils import wait_until_healthy, sync_admin_password, file_exists
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
json_logging = os.environ.get("JSON_LOGGING", "False") == "True"


logger = logging.getLogger()
logger.setLevel(logging.INFO)
if json_logging:
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)


async def main() -> None:
    parse_args()

    client = HarborAsyncClient(
        url=api_url,
        username=admin_username,
        secret=new_admin_password,
        timeout=100,
        verify=False,
    )

    logger.info("Waiting for healthy harbor")
    await wait_until_healthy(client, logger)

    logger.info("Update admin password")
    await sync_admin_password(client, logger)

    path = config_folder_path + "/configurations.json"
    if file_exists(path, logger):
        await sync_harbor_configuration(client, path, logger)

    path = config_folder_path + "/registries.json"
    if file_exists(path, logger):
        await sync_registries(client, path, logger)

    path = config_folder_path + "/projects.json"
    if file_exists(path, logger):
        await sync_projects(client, path, logger)

    path = config_folder_path + "/project-members.json"
    if file_exists(path, logger):
        await sync_project_members(client, path, logger)

    path = config_folder_path + "/robots.json"
    if file_exists(path, logger):
        await sync_robot_accounts(client, path, logger)

    path = config_folder_path + "/webhooks.json"
    if file_exists(path, logger):
        await sync_webhooks(client, path, logger)

    path = config_folder_path + "/purge-job-schedule.json"
    if file_exists(path, logger):
        await sync_purge_job_schedule(client, path, logger)

    path = config_folder_path + "/garbage-collection-schedule.json"
    if file_exists(path, logger):
        await sync_garbage_collection_schedule(client, path, logger)

    path = config_folder_path + "/retention-policies.json"
    if file_exists(path, logger):
        await sync_retention_policies(client, path, logger)


def parse_args():
    parser = argparse.ArgumentParser(
        description="""Harbor Day 2 operator to sync harbor configs""",
    )
    args = parser.parse_args()
    return args


asyncio.run(main())
