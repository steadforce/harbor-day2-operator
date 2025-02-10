from time import sleep
import os
import json
from pathlib import Path

import chevron
import re

from harborapi.models import ProjectMemberEntity
from harborapi import HarborAsyncClient
from harborapi.exceptions import Unauthorized


admin_username = os.environ.get("ADMIN_USERNAME", "admin")
old_admin_password = os.environ.get("ADMIN_PASSWORD_OLD")
new_admin_password = os.environ.get("ADMIN_PASSWORD_NEW")
api_url = os.environ.get("HARBOR_API_URL")


def file_exists(path: str, logger) -> bool:
    if os.path.exists(path):
        return True
    else:
        logger.info("File not found - skipping step", extra={"path": path})
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


def load_json(path: str) -> dict:
    """Load JSON data from a file.

    Args:
        path: Path to the JSON file.

    Returns:
        dict: The loaded JSON data.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    with open(file_path, 'r') as f:
        return json.load(f)


async def fill_template(client, path: str, logger) -> str:
    """Takes the path to a template file and returns its content with the
    replaced ids
    """
    with open(path, 'r') as file:
        content = file.read()
        placeholders = re.findall(
            r'{{[ ]*(?:project|registry):[A-z,0-9,.,\-,_]+[ ]*}}', content
        )
        logger.info("Found id templates", extra={"placeholders": placeholders})
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
