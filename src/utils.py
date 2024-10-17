from time import sleep
import os
from harborapi.models import ProjectMemberEntity
from harborapi import HarborAsyncClient
from harborapi.exceptions import Unauthorized


def check_file_exists(path: str) -> bool:
    if os.path.exists(path):
        return True
    else:
        print(f"File {filname} not found - skipping step")
        return False


async def wait_until_healthy(client) -> None:
    while True:
        health = await client.health_check()
        if health.status == "healthy":
            print("- Harbor is healthy")
            break
        print("- Waiting for harbor to become healthy...")
        sleep(5)


async def update_password(client) -> None:
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


async def sync_admin_password(client) -> None:
    try:
        await client.get_current_user()
    except Unauthorized:
        await update_password(client)


def get_member_id(members: [ProjectMemberEntity], username: str) -> int | None:
    """Returns member id of username or None if username is not in members"""
    for member in members:
        if member.entity_name == username:
            return member.id
    return None
