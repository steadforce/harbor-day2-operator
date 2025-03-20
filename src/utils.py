import os
import json
import re
from pathlib import Path
from time import sleep
from typing import Dict, Any
from logging import Logger

import chevron
from harborapi import HarborAsyncClient


# Environment variables for Harbor configuration
API_URL = os.environ.get("HARBOR_API_URL")


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

            placeholders = re.findall(
                r'{{\s*(?:project|registry):[\w.\-_]+\s*}}',
                content
            )
            logger.info("Found id templates", extra={"placeholders": placeholders})

            replacements: Dict[str, Any] = {}
            for placeholder in (p.strip(" {}") for p in placeholders):
                try:
                    placeholder_type, placeholder_value = placeholder.split(':')
                    replacement_value = await fetch_id(
                        client, placeholder_type, placeholder_value, logger
                    )

                    insert_into_dict(replacements, placeholder.split('.') + [str(replacement_value)])
                
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
    placeholder_value: str,
    logger: Logger
) -> int:
    """Fetch Harbor ID for a given placeholder.

    Args:
        client: Harbor API client instance
        placeholder_type: Type of the placeholder ('project' or 'registry')
        placeholder_value: Name of the project or registry
        logger: Logger instance for recording operations

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
        
        if len(projects) > 1:
            logger.warning(
                f"Multiple projects found with name '{placeholder_value}', using first match",
                extra={"project_count": len(projects)}
            )
        return projects[0].project_id
        
    if placeholder_type == "registry":
        registries = await client.get_registries(
            query=f"name={placeholder_value}"
        )
        if not registries:
            raise IndexError(f"Registry not found: {placeholder_value}")
        
        if len(registries) > 1:
            logger.warning(
                f"Multiple registries found with name '{placeholder_value}', using first match",
                extra={"registry_count": len(registries)}
            )
        return registries[0].id
        
    raise ValueError(f"Invalid placeholder type: {placeholder_type}")
    

def insert_into_dict(d: dict, parts: [str]) -> None:
    """Inserts nested keys and value into a dictionary.

    Args:
        d: Dictionary to insert into
        parts: List of splitted parts
    """
    *keys, last_key, value = parts
    for key in keys:
        d = d.setdefault(key, {})
    d[last_key] = value

