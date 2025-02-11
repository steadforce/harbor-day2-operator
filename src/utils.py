import os
import json
import re
from pathlib import Path
from time import sleep
from typing import Dict, Any, List, Optional
from logging import Logger

import chevron
from harborapi import HarborAsyncClient
from harborapi.models import ProjectMemberEntity, User
from harborapi.exceptions import Unauthorized


# Environment variables for Harbor configuration
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
OLD_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD_OLD")
NEW_ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD_NEW")
API_URL = os.environ.get("HARBOR_API_URL")


def file_exists(path: str, logger: Logger) -> bool:
    """Check if a file exists at the given path.

    Args:
        path: Path to the file to check
        logger: Logger instance for recording operations

    Returns:
        bool: True if file exists, False otherwise
    """
    if os.path.exists(path):
        return True
    
    logger.info("File not found - skipping step", extra={"path": path})
    return False


async def wait_until_healthy(client: HarborAsyncClient, logger: Logger) -> None:
    """Wait until the Harbor instance is healthy.

    This function polls the Harbor health check endpoint until it returns
    a healthy status.

    Args:
        client: Harbor API client instance
        logger: Logger instance for recording operations
    """
    while True:
        try:
            health = await client.health_check()
            if health.status == "healthy":
                logger.info("Harbor is healthy")
                break
            logger.info("Waiting for harbor to become healthy")
        except Exception as e:
            logger.warning(
                "Health check failed",
                extra={"error": str(e)}
            )
        sleep(5)


async def update_password(client: HarborAsyncClient, logger: Logger) -> None:
    """Update the Harbor admin password.

    This function attempts to update the admin password from OLD_ADMIN_PASSWORD
    to NEW_ADMIN_PASSWORD using the provided client.

    Args:
        client: Harbor API client instance
        logger: Logger instance for recording operations

    Raises:
        Unauthorized: If the old password is incorrect
        Exception: If any other error occurs during password update
    """
    try:
        logger.info("Starting admin password update")
        
        # Create client with old password
        old_password_client = HarborAsyncClient(
            url=API_URL,
            username=ADMIN_USERNAME,
            secret=OLD_ADMIN_PASSWORD,
            timeout=10,
            verify=False,
        )

        # Get current user details
        try:
            admin: User = await old_password_client.get_current_user()
        except Exception as e:
            logger.error("Failed to get current user", extra={"error": str(e)})
            raise

        # Update password
        try:
            await old_password_client.set_user_password(
                user_id=admin.user_id,
                old_password=OLD_ADMIN_PASSWORD,
                new_password=NEW_ADMIN_PASSWORD,
            )
            logger.info("Admin password updated successfully")
        except Exception as e:
            logger.error("Failed to update password", extra={"error": str(e)})
            raise

    except Unauthorized:
        logger.error("Unable to change admin password: unauthorized")
        raise
    except Exception as e:
        logger.error("Failed to update admin password", extra={"error": str(e)})
        raise


async def sync_admin_password(client: HarborAsyncClient, logger: Logger) -> None:
    """Synchronize admin password if current credentials are invalid.

    This function checks if the current admin credentials are valid and
    updates them if necessary.

    Args:
        client: Harbor API client instance
        logger: Logger instance for recording operations
    """
    try:
        await client.get_current_user()
    except Unauthorized:
        await update_password(client, logger)
    except Exception as e:
        logger.error("Failed to check current user", extra={"error": str(e)})
        raise


def load_json(path: str) -> Dict[str, Any]:
    """Load JSON data from a file.

    Args:
        path: Path to the JSON file

    Returns:
        Dict[str, Any]: Parsed JSON data

    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file is not valid JSON
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    with open(file_path, 'r') as f:
        return json.load(f)


async def fill_template(client: HarborAsyncClient, path: str, logger: Logger) -> str:
    """Fill a template file with Harbor-specific values.

    This function reads a template file and replaces placeholders with actual
    Harbor IDs. Placeholders should be in the format {{project:name}} or
    {{registry:name}}.

    Args:
        client: Harbor API client instance
        path: Path to the template file
        logger: Logger instance for recording operations

    Returns:
        str: Filled template content

    Raises:
        FileNotFoundError: If the template file doesn't exist
        KeyError: If a required placeholder value is not found
        Exception: If any Harbor API operation fails
    """
    try:
        with open(path, 'r') as file:
            content = file.read()
            
            # Find all placeholders in the template
            placeholders = re.findall(
                r'{{[ ]*(?:project|registry):[A-z,0-9,.,\-,_]+[ ]*}}',
                content
            )
            logger.info("Found ID templates", extra={"placeholders": placeholders})
            
            # Clean up placeholder format
            placeholders = [
                placeholder.replace('{{', '').replace(' ', '').replace('}}', '')
                for placeholder in placeholders
            ]
            
            # Build replacements dictionary
            replacements: Dict[str, Any] = {}
            for placeholder in placeholders:
                try:
                    placeholder_type, placeholder_value = placeholder.split(':')
                    replacement_value = await fetch_id(
                        client, placeholder_type, placeholder_value
                    )
                    
                    # The mustache specification, which the chevron library builds
                    # on top of, does not allow for dots in keys. Instead, keys with
                    # dots are meant to reference nested objects. In order to have
                    # the right objects to reference, nested objects / dictionaries
                    # are created for keys with dots.

                    # Handle nested dictionary creation for dot notation
                    last_part = str(replacement_value)
                    for part in reversed(placeholder.split('.')):
                        last_part = {part: last_part}
                    replacements.update(last_part)
                    
                except Exception as e:
                    logger.error(
                        "Failed to process template placeholder",
                        extra={
                            "placeholder": placeholder,
                            "error": str(e)
                        }
                    )
                    raise
            
            return chevron.render(content, replacements)
            
    except FileNotFoundError:
        logger.error("Template file not found", extra={"path": path})
        raise
    except Exception as e:
        logger.error(
            "Failed to fill template",
            extra={"path": path, "error": str(e)}
        )
        raise


async def fetch_id(
    client: HarborAsyncClient,
    placeholder_type: str,
    placeholder_value: str
) -> int:
    """Fetch Harbor ID for a given placeholder.

    Args:
        client: Harbor API client instance
        placeholder_type: Type of the placeholder ('project' or 'registry')
        placeholder_value: Name of the project or registry

    Returns:
        int: Harbor ID for the requested resource

    Raises:
        ValueError: If placeholder_type is not valid
        IndexError: If no matching resource is found
        Exception: If any Harbor API operation fails
    """
    if placeholder_type == "project":
        projects = await client.get_projects(
            query=f"name={placeholder_value}"
        )
        if not projects:
            raise IndexError(f"Project not found: {placeholder_value}")
        return projects[0].project_id
        
    if placeholder_type == "registry":
        registries = await client.get_registries(
            query=f"name={placeholder_value}"
        )
        if not registries:
            raise IndexError(f"Registry not found: {placeholder_value}")
        return registries[0].id
        
    raise ValueError(f"Invalid placeholder type: {placeholder_type}")
