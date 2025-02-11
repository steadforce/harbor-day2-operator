"""Harbor project members management module.

This module handles the synchronization of Harbor project members,
including role assignments and member management.
"""

import logging
import json
from enum import Enum
from typing import Sequence

from harborapi.client import HarborAsyncClient
from harborapi.models import ProjectMemberEntity
from harborapi.exceptions import NotFound, HarborAPIException

from .utils import load_json


class ProjectRole(Enum):
    """Enumeration of available project roles in Harbor."""
    ADMIN = 1
    DEVELOPER = 2
    GUEST = 3
    MAINTAINER = 4


async def remove_unlisted_members(
    client: HarborAsyncClient,
    project_name: str,
    current_members: Sequence[ProjectMemberEntity],
    target_members: Sequence[ProjectMemberEntity],
    logger: logging.Logger
) -> None:
    """Remove project members that are not in the target list.

    Args:
        client: Harbor API client instance.
        project_name: Name of the project.
        current_members: List of current project members.
        target_members: List of desired project members.
        logger: Logger instance for output.
    """
    target_usernames = {member.entity_name for member in target_members}
    
    for current_member in current_members:
        if current_member.entity_name not in target_usernames:
            logger.info(
                "Removing member from project",
                extra={
                    "member": current_member.entity_name,
                    "project": project_name
                }
            )
            try:
                await client.remove_project_member(
                    project_name_or_id=project_name,
                    member_id=current_member.id,
                )
            except HarborAPIException as e:
                logger.error(
                    "Failed to remove project member: %s",
                    str(e),
                    extra={
                        "member": current_member.entity_name,
                        "project": project_name
                    }
                )
                raise


async def sync_member_roles(
    client: HarborAsyncClient,
    project_name: str,
    current_members: Sequence[ProjectMemberEntity],
    target_members: Sequence[ProjectMemberEntity],
    logger: logging.Logger
) -> None:
    """Synchronize project member roles and add new members.

    Args:
        client: Harbor API client instance.
        project_name: Name of the project.
        current_members: List of current project members.
        target_members: List of desired project members.
        logger: Logger instance for output.
    """
    for target_member in target_members:
        existing_member_id = next(
            (existing.id for existing in current_members if existing.entity_name == target_member.entity_name),
            None
        )
        
        try:
            if existing_member_id:  # Update existing member
                logger.info(
                    "Updating project role for member",
                    extra={
                        "member": target_member.entity_name,
                        "project": project_name,
                        "role": target_member.role_id
                    }
                )
                await client.update_project_member_role(
                    project_name_or_id=project_name,
                    member_id=existing_member_id,
                    role=target_member.role_id,
                )
            else:  # Add new member
                logger.info(
                    "Adding new member to project",
                    extra={
                        "member": target_member.entity_name,
                        "project": project_name,
                        "role": target_member.role_id
                    }
                )
                await client.add_project_member_user(
                    project_name_or_id=project_name,
                    username_or_id=target_member.entity_name,
                    role_id=target_member.role_id,
                )
        except NotFound:
            logger.warning(
                "User not found - skipping",
                extra={
                    "member": target_member.entity_name,
                    "hint": "Make sure user has logged in at least once"
                }
            )
        except HarborAPIException as e:
            logger.error(
                "Failed to manage project member: %s",
                str(e),
                extra={
                    "member": target_member.entity_name,
                    "project": project_name
                }
            )
            raise


async def sync_project_members(
    client: HarborAsyncClient,
    path: str,
    logger: logging.Logger
) -> None:
    """Synchronize project members and their roles from a configuration file.

    The function will:
    1. Load the project members configuration from the specified file
    2. For each project:
        - Get current members
        - Remove members not in the config
        - Update roles for existing members
        - Add new members with specified roles

    Args:
        client: Harbor API client instance.
        path: Path to the project members configuration file.
        logger: Logger instance for output.

    Raises:
        FileNotFoundError: If the configuration file doesn't exist.
        json.JSONDecodeError: If the configuration file is not valid JSON.
        HarborAPIException: If any Harbor API request fails.
    """
    try:
        logger.info("Loading project members configuration from %s", path)
        config = load_json(path)
        
        for project in config:
            project_name = project["project_name"]
            logger.info(
                "Syncing project members",
                extra={"project": project_name}
            )

            # Get current members
            current_members = await client.get_project_members(
                project_name_or_id=project_name,
                limit=None
            )

            # Build target member list
            target_members = []
            for role in ProjectRole:
                role_members = project.get(role.name.lower(), [])
                target_members.extend([
                    ProjectMemberEntity(
                        entity_name=username,
                        role_id=role.value
                    )
                    for username in role_members
                ])

            # Sync members
            await remove_unlisted_members(
                client, project_name, current_members, target_members, logger
            )
            await sync_member_roles(
                client, project_name, current_members, target_members, logger
            )

    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error("Failed to load project members configuration: %s", str(e))
        raise
    except HarborAPIException as e:
        logger.error("Failed to sync project members: %s", str(e))
        raise
