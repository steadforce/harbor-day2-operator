from time import sleep
import os

import chevron
import re

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


async def fill_template(client, path: str) -> str:
    """Takes the path to a template file and returns its content with the
    replaced ids
    """
    with open(path, 'r') as file:
        content = file.read()
        placeholders = re.findall(
            r'{{[ ]*(?:project|registry):[A-z,0-9,.,\-,_]+[ ]*}}', content
        )
        print(f"Found id templates: {placeholders}")
        placeholders = [
            placeholder.replace('{{', '').replace(' ', '').replace('}}', '')
            for placeholder in placeholders
        ]
        replacements = {}
        for placeholder in placeholders:
            placeholder_type, placeholder_value = placeholder.split(':')
            replacement_value = await fetch_id(
                client, placeholder_type, placeholder_value
            )
            # The mustache specification, which the chevron library builds
            # on top of, does not allow for dots in keys. Instead, keys with
            # dots are meant to reference nested objects. In order to have
            # the right objects to reference, nested objects / dictionaries
            # are created for keys with dots.
            last_part = str(replacement_value)
            for part in reversed(placeholder.split('.')):
                last_part = {part: last_part}
            replacements = replacements | last_part
        config = chevron.render(content, replacements)
        return config


async def fetch_id(
    client, placeholder_type: str, placeholder_value: str
) -> int:
    """Fetches the id of an object with the given name"""
    if placeholder_type == "project":
        projects = await client.get_projects(
            query=f"name={placeholder_value}"
        )
        project = projects[0]
        project_id = project.project_id
        return project_id
    if placeholder_type == "registry":
        registries = await client.get_registries(
            query=f"name={placeholder_value}"
        )
        registry = registries[0]
        registry_id = registry.id
        return registry_id
