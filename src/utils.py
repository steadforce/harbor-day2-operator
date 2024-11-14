from time import sleep
import os
from harborapi.models import ProjectMemberEntity
from harborapi import HarborAsyncClient
from harborapi.exceptions import Unauthorized


admin_username = os.environ.get("ADMIN_USERNAME", "admin")
old_admin_password = os.environ.get("ADMIN_PASSWORD_OLD")
new_admin_password = os.environ.get("ADMIN_PASSWORD_NEW")
api_url = os.environ.get("HARBOR_API_URL")


def check_file_exists(path: str) -> bool:
    if os.path.exists(path):
        return True
    else:
        print(f"File {path} not found - skipping step")
        return False


async def wait_until_healthy(client, logger) -> None:
    while True:
        health = await client.health_check()
        if health.status == "healthy":
            logger.info("Harbor is healthy")
            break
        logger.info("Waiting for harbor to become healthy")
        sleep(5)


async def update_password(client, logger) -> None:
    try:
        logger.info("Updating password")
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
        logger.info("Updated admin password")
    except Unauthorized:
        logger.error("Unable to change the admin password")


async def sync_admin_password(client, logger) -> None:
    try:
        await client.get_current_user()
    except Unauthorized:
        await update_password(client, logger)


def get_member_id(members: [ProjectMemberEntity], username: str) -> int | None:
    """Returns member id of username or None if username is not in members"""
    for member in members:
        if member.entity_name == username:
            return member.id
    return None
