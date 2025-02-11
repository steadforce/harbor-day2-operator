import json
import os
from typing import List, Dict, Any
from logging import Logger

from harborapi.models import Robot
from harborapi.exceptions import Conflict, BadRequest

from utils import load_json


ROBOT_NAME_PREFIX = os.environ.get("ROBOT_NAME_PREFIX", "")


async def sync_robot_accounts(client: Any, path: str, logger: Logger) -> None:
    """Synchronize Harbor robot accounts with configuration file.

    This function performs the following operations:
    1. Loads robot account configurations from file
    2. Retrieves existing robot accounts (both system and project level)
    3. Deletes robot accounts that exist in Harbor but not in config
    4. Updates existing robot accounts or creates new ones
    5. Sets robot secrets from environment variables if available

    Args:
        client: Harbor API client instance
        path: Path to the robot accounts configuration file
        logger: Logger instance for recording operations

    Raises:
        FileNotFoundError: If the configuration file does not exist
        json.JSONDecodeError: If the configuration file is not valid JSON
        Exception: If any Harbor API operation fails
    """
    logger.info("Starting robot account synchronization")

    try:
        # Load robot configurations
        try:
            target_robots = load_json(path)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(
                "Failed to load robot configuration",
                extra={"path": path, "error": str(e)}
            )
            raise

        # Fetch all existing robots
        try:
            current_robots = await get_all_robots(client, logger)
            current_robot_map = {robot.name: robot for robot in current_robots}
        except Exception as e:
            logger.error("Failed to fetch existing robots", extra={"error": str(e)})
            raise

        # Get target robot names with proper prefixes
        target_robots_with_names = []
        for target_robot in target_robots:
            try:
                full_name = await construct_full_robot_name(target_robot)
                target_robots_with_names.append((full_name, target_robot))
            except KeyError as e:
                logger.error(
                    "Invalid robot configuration",
                    extra={"robot": target_robot, "error": f"Missing field: {str(e)}"}
                )
                raise

        target_robot_names = {name for name, _ in target_robots_with_names}

        # Delete robots not in config
        for robot_name, robot in current_robot_map.items():
            if robot_name not in target_robot_names:
                try:
                    logger.info(
                        "Deleting robot not in config",
                        extra={"robot": robot_name}
                    )
                    await client.delete_robot(robot_id=robot.id)
                except Exception as e:
                    logger.error(
                        "Failed to delete robot",
                        extra={"robot": robot_name, "error": str(e)}
                    )
                    raise

        # Update or create robots
        for full_name, target_config in target_robots_with_names:
            try:
                target_robot = Robot(**target_config)
                original_name = target_robot.name
                target_robot.name = full_name

                if full_name in current_robot_map:
                    # Update existing robot
                    robot_id = current_robot_map[full_name].id
                    logger.info(
                        "Updating existing robot",
                        extra={"robot": full_name, "robot_id": robot_id}
                    )
                    await client.update_robot(robot_id=robot_id, robot=target_robot)
                    await set_robot_secret(client, original_name, robot_id, logger)
                else:
                    # Create new robot
                    try:
                        logger.info(
                            "Creating new robot",
                            extra={"robot": full_name}
                        )
                        created_robot = await client.create_robot(robot=target_robot)
                        await set_robot_secret(
                            client, original_name, created_robot.id, logger
                        )
                    except (Conflict, BadRequest) as e:
                        logger.error(
                            "Failed to create robot",
                            extra={"robot": full_name, "error": str(e)}
                        )
                        continue

            except Exception as e:
                logger.error(
                    "Failed to process robot configuration",
                    extra={"robot": full_name, "error": str(e)}
                )
                raise

        logger.info("Robot account synchronization completed successfully")

    except Exception as e:
        logger.error("Robot account synchronization failed", extra={"error": str(e)})
        raise


async def get_all_robots(client: Any, logger: Logger) -> List[Robot]:
    """Fetch all robot accounts from Harbor (both system and project level).

    Args:
        client: Harbor API client instance
        logger: Logger instance for recording operations

    Returns:
        List[Robot]: Combined list of system and project level robots

    Raises:
        Exception: If fetching robots fails
    """
    # Get system level robots
    system_robots = await client.get_robots(query='Level=system', limit=None)
    
    # Get project level robots
    projects = await client.get_projects(limit=None)
    project_robots = []
    
    for project in projects:
        robots = await client.get_robots(
            query=f'Level=project,ProjectID={project.project_id}',
            limit=None
        )
        project_robots.extend(robots)
    
    return system_robots + project_robots


async def construct_full_robot_name(target_robot: Dict[str, Any]) -> str:
    """Construct the full robot name including prefix and namespace if applicable.

    Args:
        target_robot: Robot configuration dictionary

    Returns:
        str: Full robot name with prefix and namespace

    Raises:
        KeyError: If required fields are missing from configuration
    """
    namespace = target_robot['permissions'][0]['namespace']
    robot_name = target_robot['name']
    
    if namespace != '*':
        return f'{ROBOT_NAME_PREFIX}{namespace}+{robot_name}'
    return f'{ROBOT_NAME_PREFIX}{robot_name}'


async def set_robot_secret(
    client: Any,
    robot_name: str,
    robot_id: int,
    logger: Logger
) -> None:
    """Set robot account secret from environment variable if available.

    The environment variable name is constructed by converting the robot name
    to uppercase and replacing hyphens with underscores.

    Args:
        client: Harbor API client instance
        robot_name: Original robot name (without prefix/namespace)
        robot_id: Robot account ID
        logger: Logger instance for recording operations
    """
    env_var_name = robot_name.upper().replace("-", "_")
    secret = os.environ.get(env_var_name)
    
    if secret:
        try:
            logger.info("Setting robot secret", extra={"robot": robot_name})
            await client.refresh_robot_secret(robot_id, secret)
        except Exception as e:
            logger.error(
                "Failed to set robot secret",
                extra={"robot": robot_name, "error": str(e)}
            )
            raise
    else:
        logger.info(
            "No robot secret found in environment",
            extra={"robot": robot_name, "env_var": env_var_name}
        )
