import asyncio
from enum import Enum

# API calls to configure harbor:
# See Harbor api: https://harbor.dev.k8s01.steadforce.com/devcenter-api-2.0
from harborapi import HarborAsyncClient
from harborapi.exceptions import NotFound, Unauthorized, Conflict, BadRequest
from harborapi.models import (
    Robot,
    Configurations,
    Registry,
    WebhookPolicy,
    Project,
    ProjectMemberEntity,
)
import argparse
import json
import os
from time import sleep


class ProjectRole(Enum):
    ADMIN = 1
    DEVELOPER = 2
    GUEST = 3
    MAINTAINER = 4


admin_username = "admin"
old_admin_password = os.environ.get("ADMIN_PASSWORD_OLD")
new_admin_password = os.environ.get("ADMIN_PASSWORD_NEW")
api_url = os.environ.get("HARBOR_API_URL")
config_folder_path = os.environ.get("CONFIG_FOLDER_PATH")
robot_name_prefix = os.environ.get("ROBOT_NAME_PREFIX")
oidc_client_secret = os.environ.get("OIDC_STATIC_CLIENT_TOKEN")
oidc_endpoint = os.environ.get("OIDC_ENDPOINT")


async def main() -> None:
    parse_args()

    global client
    client = HarborAsyncClient(
        url=api_url,
        username=admin_username,
        secret=new_admin_password,
        timeout=100,
        verify=False,
    )

    # Wait for healthy harbor
    print("WAITING FOR HEALTHY HARBOR")
    await wait_until_healthy()
    print("")

    # Update admin password
    print("UPDATE ADMIN PASSWROD")
    await sync_admin_password()
    print("")

    # Sync harbor configuration
    print("SYNCING HARBOR CONFIGURATION")
    harbor_config = json.load(
        open(config_folder_path + "/configurations.json")
    )
    harbor_config = Configurations(**harbor_config)
    harbor_config.oidc_client_secret = oidc_client_secret
    harbor_config.oidc_endpoint = oidc_endpoint
    await sync_harbor_config(harbor_config=harbor_config)
    print("")

    # Sync registries
    print("SYNCING REGISTRIES")
    registries_config = json.load(
        open(config_folder_path + "/registries.json")
    )
    await sync_registries(target_registries=registries_config)
    print("")

    # Sync projects
    print("SYNCING PROJECTS")
    projects_config = json.load(open(config_folder_path + "/projects.json"))
    await sync_projects(target_projects=projects_config)
    print("")

    # Sync project members and their roles
    print("SYNCING PROJECT MEMBERS")
    project_members_config = json.load(
        open(config_folder_path + "/project-members.json")
    )
    for project in project_members_config:
        await sync_project_members(project=project)
    print("")

    # Sync robot accounts
    print("SYNCING ROBOT ACCOUNTS")
    robot_config = json.load(open(config_folder_path + "/robots.json"))
    await sync_robot_accounts(target_robots=robot_config)
    print("")

    # Sync webhooks
    print("SYNCING WEBHOOKS")
    webhooks_config = json.load(open(config_folder_path + "/webhooks.json"))
    for webhook in webhooks_config:
        await sync_webhook(**webhook)
    print("")


async def sync_harbor_config(harbor_config: Configurations):
    await client.update_config(harbor_config)


async def sync_registries(target_registries: [Registry]):
    current_registries = await client.get_registries()
    current_registry_names = [
        current_registry.name for current_registry in current_registries
    ]
    current_registry_id = [
        current_registry.id for current_registry in current_registries
    ]
    target_registry_names = [
        target_registry["name"] for target_registry in target_registries
    ]

    # Delete all registries not defined in config file
    for current_registry in current_registries:
        if current_registry.name not in target_registry_names:
            print(
                f'- Deleting registry "{current_registry.name}" since it is'
                " not defined in config files"
            )
            await client.delete_registry(id=current_registry.id)

    # Modify existing registries or create new ones
    for target_registry in target_registries:
        # Modify existing registry
        if target_registry["name"] in current_registry_names:
            registry_id = current_registry_id[
                current_registry_names.index(target_registry["name"])
            ]
            print(f'- Syncing registry "{target_registry["name"]}"')
            await client.update_registry(
                id=registry_id, registry=target_registry
            )
        # Create new registry
        else:
            print(f'- Creating new registry "{target_registry["name"]}"')
            await client.create_registry(registry=target_registry)


async def sync_robot_accounts(target_robots: [Robot]):
    current_robots = await client.get_robots()
    current_robot_names = [
        current_robot.name for current_robot in current_robots
    ]
    current_robot_id = [current_robot.id for current_robot in current_robots]

    # Harbor appends a prefix to all robot account names
    # To compare against our target robot names, we have to add the prefix
    target_robot_names_with_prefix = [
        robot_name_prefix + target_robot["name"]
        for target_robot in target_robots
    ]

    # Delete all robots not defined in config file
    for current_robot in current_robots:
        if current_robot.name not in target_robot_names_with_prefix:
            print(
                f'- Deleting robot "{current_robot.name}" since it is not'
                " defined in config files"
            )
            await client.delete_robot(robot_id=current_robot.id)

    # Modify existing robots or create new ones
    for target_robot in target_robots:
        target_robot = Robot(**target_robot)
        target_robot.secret = os.environ.get(
            target_robot.name.upper().replace("-", "_")
        )
        # Modify existing robot
        if robot_name_prefix + target_robot.name in current_robot_names:
            robot_id = current_robot_id[
                current_robot_names.index(
                    robot_name_prefix + target_robot.name
                )
            ]
            target_robot.name = robot_name_prefix + target_robot.name
            print(f'- Syncing robot "{target_robot.name}".')
            await client.update_robot(robot_id=robot_id, robot=target_robot)
        # Create new robot
        else:
            print(
                "- Creating new robot"
                f' "{robot_name_prefix + target_robot.name}"'
            )
            try:
                await client.create_robot(robot=target_robot)
            except Conflict:
                print(
                    f'  => ERROR: "{robot_name_prefix + target_robot.name}"'
                    " already present. Manually delete this account to create"
                    " an updated one"
                )
            except BadRequest as e:
                print(f'Bad request permission: {e}')


async def sync_webhook(project_name: str, policies: list[WebhookPolicy]):
    print(f'PROJECT: "{project_name}"')

    target_policies = policies
    current_policies = await client.get_webhook_policies(
        project_name_or_id=project_name
    )
    current_policy_names = [
        current_policy.name for current_policy in current_policies
    ]
    current_policy_id = [
        current_policy.id for current_policy in current_policies
    ]
    target_policy_names = [
        target_policy["name"] for target_policy in target_policies
    ]

    # Delete all policies not defined in config file
    for current_policy in current_policies:
        if current_policy.name not in target_policy_names:
            print(
                f'- Deleting policy "{current_policy.name}" since it is not'
                " defined in config files"
            )
            await client.delete_webhook_policy(
                project_name_or_id=project_name,
                webhook_policy_id=current_policy.id,
            )

    # Modify existing policies or create new ones
    for target_policy in target_policies:
        # Modify existing policy
        if target_policy["name"] in current_policy_names:
            policy_id = current_policy_id[
                current_policy_names.index(target_policy["name"])
            ]
            print(f'- Syncing policy "{target_policy["name"]}"')
            await client.update_webhook_policy(
                project_name_or_id=project_name,
                webhook_policy_id=policy_id,
                policy=target_policy,
            )
        # Create new policy
        else:
            print(f'- Creating new policy "{target_policy["name"]}"')
            await client.create_webhook_policy(
                project_name_or_id=project_name, policy=target_policy
            )


async def sync_projects(target_projects: [Project]) -> None:
    current_projects = await client.get_projects()
    current_project_names = [
        current_project.name for current_project in current_projects
    ]
    target_project_names = [
        target_project["project_name"] for target_project in target_projects
    ]

    # Delete all projects not defined in config file
    for current_project in current_projects:
        if current_project.name not in target_project_names:
            repositories = await client.get_repositories(
                project_name=current_project.name
            )
            if len(repositories) == 0:
                print(
                    f'- Deleting project "{current_project.name}" since it is'
                    " empty and not defined in config files"
                )
                await client.delete_project(
                    project_name_or_id=current_project.name
                )
            else:
                print(
                    f'- Deletion of project "{current_project.name}" not'
                    " possible since it is not empty"
                )

    # Modify existing projects or create new ones
    for target_project in target_projects:
        # Modify existing project
        if target_project["project_name"] in current_project_names:
            print(f'- Syncing project "{target_project["project_name"]}"')
            await client.update_project(
                project_name_or_id=current_project.name, project=target_project
            )
        # Create new project
        else:
            print(f'- Creating new project "{target_project["project_name"]}"')
            await client.create_project(project=target_project)


async def sync_project_members(project) -> None:
    project_name = project["project_name"]
    print(f'PROJECT: "{project_name}"')

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
                f'- Removing "{current_member.entity_name}" from project'
                f' "{project_name}"'
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
            print(f'- Syncing project role of "{member.entity_name}"')
            await client.update_project_member_role(
                project_name_or_id=project_name,
                member_id=member_id,
                role=member.role_id,
            )
        # Add new member
        else:
            print(
                f'- Adding new member "{member.entity_name}" to project'
                f' "{project_name}"'
            )
            try:
                await client.add_project_member_user(
                    project_name_or_id=project_name,
                    username_or_id=member.entity_name,
                    role_id=member.role_id,
                )
            except NotFound:
                print(
                    f'  => ERROR: User "{member.entity_name}" not found. Make'
                    " sure the user has logged into harbor at least once"
                )


async def wait_until_healthy() -> None:
    while True:
        health = await client.health_check()
        if health.status == "healthy":
            print("- Harbor is healthy")
            break
        print("- Waiting for harbor to become healthy...")
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
        print("- Updated admin password")
    except Unauthorized:
        print(
            "- Admin password remains unchanged since it is does not match the"
            "  old admin password password"
        )


def get_member_id(members: [ProjectMemberEntity], username: str) -> int | None:
    """Returns member id of username or None if username is not in members"""
    for member in members:
        if member.entity_name == username:
            return member.id
    return None


def parse_args():
    parser = argparse.ArgumentParser(
        description="""Harbor Day 2 configurator to sync harbor configs""",
    )
    args = parser.parse_args()
    return args


asyncio.run(main())
