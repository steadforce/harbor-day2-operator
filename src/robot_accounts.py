import json
import os
from harborapi.models import Robot
from harborapi.exceptions import Conflict, BadRequest


robot_name_prefix = os.environ.get("ROBOT_NAME_PREFIX")


async def sync_robot_accounts(client, path, logger):
    """Synchronize all robot accounts

    All robot accounts from the robot accounts file, if existent,
    will be updated and applied to harbor.
    """

    logger.info("Syncing robot accounts")
    target_robots = json.load(open(path))

    # Get all system level robots
    current_system_robots = await client.get_robots(
        query='Level=system',
        limit=None,
    )

    # Get all project level robots
    current_projects = await client.get_projects(limit=None)
    current_project_ids = [
        current_project.project_id
        for current_project in current_projects
    ]
    current_projects_robots = []
    for current_project_id in current_project_ids:
        project_robots = await client.get_robots(
            query=f'Level=project,ProjectID={current_project_id}',
            limit=None
        )
        current_projects_robots += project_robots

    # Combine system and project robots to get a list of all robots
    current_robots = current_system_robots + current_projects_robots
    current_robot_names = [
        current_robot.name for current_robot in current_robots
    ]
    current_robot_id = [current_robot.id for current_robot in current_robots]

    # Harbor appends a prefix and namespace if present to all
    # robot account names.
    # To compare against our target robot names, we have to add the prefix
    target_robot_names_with_prefix = [
        await construct_full_robot_name(target_robot)
        for target_robot in target_robots
    ]

    # Delete all robots not defined in config file
    for current_robot in current_robots:
        if current_robot.name not in target_robot_names_with_prefix:
            logger.info(
                "Deleting robot as not defined",
                extra={"robot": current_robot.name}
            )
            await client.delete_robot(robot_id=current_robot.id)

    # Modify existing robots or create new ones
    for target_robot in target_robots:
        full_robot_name = await construct_full_robot_name(target_robot)
        target_robot = Robot(**target_robot)
        # Modify existing robot
        if full_robot_name in current_robot_names:
            robot_id = current_robot_id[
                current_robot_names.index(full_robot_name)
            ]
            short_robot_name = target_robot.name
            target_robot.name = full_robot_name
            logger.info("Syncing robot", extra={"robot": target_robot.name})
            await client.update_robot(robot_id=robot_id, robot=target_robot)
            await set_robot_secret(client, short_robot_name, robot_id, logger)
        # Create new robot
        else:
            logger.info("Creating new robot", extra={"robot": target_robot.name})
            try:
                created_robot = await client.create_robot(robot=target_robot)
                await set_robot_secret(
                    client, target_robot.name, created_robot.id, logger
                )
            except Conflict as e:
                logger.info("Harbor Conflict", extra={"error": e})
            except BadRequest as e:
                logger.info("Bad request", extra={"error": e})


async def construct_full_robot_name(target_robot: Robot) -> str:
    if (namespace := target_robot['permissions'][0]['namespace']) != '*':
        return f'{robot_name_prefix}{namespace}+{target_robot["name"]}'
    else:
        return f'{robot_name_prefix}{target_robot["name"]}'


async def set_robot_secret(client, robot_name: str, robot_id: int, logger):
    secret = os.environ.get(
        robot_name.upper().replace("-", "_")
    )
    if secret:
        logger.info("Set robot secret", extra={"robot": robot_name})
        await client.refresh_robot_secret(robot_id, secret)
    else:
        logger.info("No robot secret found", extra={"robot": robot_name})
