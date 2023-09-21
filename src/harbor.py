import asyncio
from enum import Enum

# API calls to configure harbor:
# See Harbor api: https://harbor.dev.k8s01.steadforce.com/devcenter-api-2.0
from harborapi import HarborAsyncClient
from harborapi.exceptions import NotFound, Unauthorized, Conflict
from harborapi.models import (
    Robot,
    Configurations,
    Registry,
    WebhookPolicy,
    Project,
    ProjectMemberEntity,
)
import json
import os
from time import sleep


class ProjectRole(Enum):
    ADMIN = 1
    DEVELOPER = 2
    GUEST = 3
    MAINTAINER = 4


admin_username = "admin"
old_admin_password = "Harbor12345"
new_admin_password = os.environ.get("ADMIN_PASSWORD")
api_url = os.environ.get("HARBOR_API_URL")
config_folder_path = os.environ.get("CONFIG_FOLDER_PATH")

client = HarborAsyncClient(
    url=api_url,
    username=admin_username,
    secret=new_admin_password,
    timeout=100,
    verify=False,
)


async def main() -> None:
    # Wait for healthy harbor
    print("Waiting for Harbor to be healthy")
    await wait_until_healthy()

    # Update admin password
    print("Update admin password")
    await sync_admin_password()

    # Sync harbor configuration
    print("Syncing Harbor configuration")
    harbor_config = json.load(
        open(config_folder_path + "/configurations.json")
    )
    harbor_config = Configurations(**harbor_config)
    harbor_config.oidc_client_secret = os.environ.get(
        "OIDC_STATIC_CLIENT_TOKEN"
    )
    harbor_config.oidc_endpoint = os.environ.get("OIDC_ENDPOINT")
    await sync_harbor_config(harbor_config=harbor_config)

    # Sync registries
    print("Syncing registries")
    registries_config = json.load(
        open(config_folder_path + "/registries.json")
    )
    for registry in registries_config:
        await sync_registry(Registry(**registry))

    # Sync projects
    print("Syncing projects")
    projects_config = json.load(open(config_folder_path + "/projects.json"))
    for project in projects_config:
        await sync_project(Project(**project))

    # Sync robot accounts
    print("Syncing robots")
    robot_config = json.load(open(config_folder_path + "/robots.json"))
    for robot in robot_config:
        await sync_robot_account(Robot(**robot))

    # Sync webhooks
    print("Syncing webhooks")
    webhooks_config = json.load(open(config_folder_path + "/webhooks.json"))
    for webhook in webhooks_config:
        await sync_webhook(**webhook)

    # Sync project members and their roles
    print("Syncing project members")
    project_members_config = json.load(
        open(config_folder_path + "/project-members.json")
    )
    for project in project_members_config:
        await sync_project_members(project=project)


async def sync_harbor_config(harbor_config: Configurations):
    await client.update_config(harbor_config)


async def sync_registry(registry: Registry):
    try:
        await client.create_registry(registry=registry)
    except Conflict:
        print(f'Registry "{registry.name}" already exists')


async def sync_robot_account(robot: Robot):
    try:
        await client.create_robot(robot)
    except Conflict:
        print(f'Robot account "{robot.name}" already exists')


async def sync_webhook(project_name: str, policies: list[WebhookPolicy]):
    # WEbhooks for AA, abbott, aek, aertze kammer  chatbot, steadop
    for policy in policies:
        try:
            await client.create_webhook_policy(
                project_name_or_id=project_name, policy=policy
            )
        except Conflict:
            print(
                f'Webhook "{policy["name"]}" in project "{project_name}" \
                    already exists'
            )


async def sync_project(project: Project) -> None:
    try:
        await client.create_project(project=project)
    except Conflict:
        print(f'Project "{project.project_name}" already exists')


async def sync_project_members(project) -> None:
    project_name = project["project_name"]

    current_members = await client.get_project_members(
        project_name_or_id=project_name
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
            print(
                f'Removing "{current_member.entity_name}" from project \
                    "{project_name}"'
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
            print(f'Syncing project role of "{member.entity_name}"')
            await client.update_project_member_role(
                project_name_or_id=project_name,
                member_id=member_id,
                role=member.role_id,
            )
        # Add new member
        else:
            print(
                f'Adding new member "{member.entity_name}" to project \
                    "{project_name}"'
            )
            try:
                await client.add_project_member_user(
                    project_name_or_id=project_name,
                    username_or_id=member.entity_name,
                    role_id=member.role_id,
                )
            except NotFound:
                print(
                    f'User "{member.entity_name}" not found. Make sure the \
                        user has logged into harbor at least once'
                )


async def wait_until_healthy() -> None:
    while True:
        health = await client.health_check()
        if health.status == "healthy":
            print("Harbor is healthy")
            break
        print("Waiting for harbor to become healthy...")
        sleep(5)


async def sync_admin_password() -> None:
    try:
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
        print("Updated admin password")
    except Unauthorized:
        print(
            'Admin password remains unchanged since it is not the initial \
                "Harbor12345" password'
        )


def get_member_id(members: [ProjectMemberEntity], username: str) -> int | None:
    """Returns member id of username or None if username is not in members"""
    for member in members:
        if member.entity_name == username:
            return member.id
    return None


asyncio.run(main())
