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


ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_NEW = os.environ.get("ADMIN_PASSWORD_NEW")
API_URL = os.environ.get("HARBOR_API_URL")
CONFIG_FOLDER_PATH = os.environ.get("CONFIG_FOLDER_PATH")
JSON_LOGGING = os.environ.get("JSON_LOGGING").lower() in ["true", "1", "yes", "y"]


logger = logging.getLogger()
logger.setLevel(logging.INFO)
if JSON_LOGGING:
    formatter = jsonlogger.JsonFormatter()
else:
    formatter = logging.Formatter()
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)


async def main() -> None:
    client = HarborAsyncClient(
        url=API_URL,
        username=ADMIN_USERNAME,
        secret=ADMIN_PASSWORD_NEW,
        timeout=100,
        verify=False,
    )

    logger.info("Waiting for healthy harbor")
    await wait_until_healthy(client, logger)

    logger.info("Update admin password")
    await sync_admin_password(client, logger)

    path = CONFIG_FOLDER_PATH + "/configurations.json"
    if file_exists(path, logger):
        await sync_harbor_configuration(client, path, logger)

    path = CONFIG_FOLDER_PATH + "/registries.json"
    if file_exists(path, logger):
        await sync_registries(client, path, logger)

    path = CONFIG_FOLDER_PATH + "/projects.json"
    if file_exists(path, logger):
        await sync_projects(client, path, logger)

    path = CONFIG_FOLDER_PATH + "/project-members.json"
    if file_exists(path, logger):
        await sync_project_members(client, path, logger)

    path = CONFIG_FOLDER_PATH + "/robots.json"
    if file_exists(path, logger):
        await sync_robot_accounts(client, path, logger)

    path = CONFIG_FOLDER_PATH + "/webhooks.json"
    if file_exists(path, logger):
        await sync_webhooks(client, path, logger)

    path = CONFIG_FOLDER_PATH + "/purge-job-schedule.json"
    if file_exists(path, logger):
        await sync_purge_job_schedule(client, path, logger)

    path = CONFIG_FOLDER_PATH + "/garbage-collection-schedule.json"
    if file_exists(path, logger):
        await sync_garbage_collection_schedule(client, path, logger)

    path = CONFIG_FOLDER_PATH + "/retention-policies.json"
    if file_exists(path, logger):
        await sync_retention_policies(client, path, logger)


asyncio.run(main())
