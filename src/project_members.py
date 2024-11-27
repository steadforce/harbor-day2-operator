import json
from enum import Enum
from harborapi.models import ProjectMemberEntity
from harborapi.exceptions import NotFound


class ProjectRole(Enum):
    ADMIN = 1
    DEVELOPER = 2
    GUEST = 3
    MAINTAINER = 4


async def sync_project_members(client, path, logger):
    """Synchronize all project members

    All project members and their roles from the project members file,
    if existent, will be updated and applied to harbor.
    """

    logger.info("Syncing project members")
    project_members_config = json.load(open(path))
    for project in project_members_config:
        project_name = project["project_name"]
        logger.info(
            "Syncing project members of project",
            extra={"project": project_name}
        )

        current_members = await client.get_project_members(
            project_name_or_id=project_name,
            limit=None
        )
        target_members = []
        for project_role in ProjectRole:
            target_members += [
                ProjectMemberEntity(
                    entity_name=username, role_id=project_role.value
                )
                for username in project[project_role.name.lower()]
            ]

        # Remove all non listed current project members
        for current_member in current_members:
            if current_member.entity_name not in [
                target_member.entity_name for target_member in target_members
            ]:
                logger.info(
                    "Removing member from project",
                    extra={
                        "member": current_member.entity_name,
                        "project": project_name
                    }
                )
                await client.remove_project_member(
                    project_name_or_id=project_name,
                    member_id=current_member.id,
                )

        # Update existing members and add new ones
        for member in target_members:
            member_id = get_member_id(current_members, member.entity_name)
            # Sync existing members' project role
            if member_id:
                logger.info(
                    "Syncing project role of member",
                    extra={"member": member.entity_name}
                )
                await client.update_project_member_role(
                    project_name_or_id=project_name,
                    member_id=member_id,
                    role=member.role_id,
                )
            # Add new member
            else:
                logger.info(
                    "Adding new member to project",
                    extra={
                        "member": member.entity_name,
                        "project": project_name
                    }
                )
                try:
                    await client.add_project_member_user(
                        project_name_or_id=project_name,
                        username_or_id=member.entity_name,
                        role_id=member.role_id,
                    )
                except NotFound:
                    logger.info(
                        "User not found",
                        extra={
                            "member": member.entity_name,
                            "hint": "Make sure user has logged in"
                        }
                    )
