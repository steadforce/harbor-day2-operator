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


async def fill_template(client, path: str, logger) -> str:
    """Reads a template file, replaces placeholders with fetched IDs, and returns the updated content."""
    with open(path, 'r') as file:
        config = file.read()

    placeholders = re.findall(r'{{\s*(?:project|registry):[\w.\-_]+\s*}}', config)
    logger.info("Found id templates", extra={"placeholders": placeholders})

    replacements = {}
    for placeholder in (p.strip(" {}") for p in placeholders):
        placeholder_type, placeholder_value = placeholder.split(':')
        replacement_value = await fetch_id(client, placeholder_type, placeholder_value)

        # Create nested dictionary structure for replacements
        insert_into_dict(replacements, placeholder.split('.') + [str(replacement_value)])

    return chevron.render(config, replacements)


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


def insert_into_dict(d: dict, parts: [str]) -> None:
    """Inserts nested keys and value into a dictionary.

    >>> d = {}
    >>> insert_into_dict(d, ["a", "b", 1])
    >>> d
    {"a": {"b": 1}}
    >>> insert_into_dict(d, ["a", "c", 2])
    >>> d
    {"a": {"b": 1, c: "2"}}
    """
    *keys, last_key, value = parts
    for key in keys:
        d = d.setdefault(key, {})
    d[last_key] = value