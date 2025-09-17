import json
import os
from typing import List, Dict, Any, Tuple
from logging import Logger

from harborapi.models import Robot
from harborapi.exceptions import Conflict, BadRequest

from utils import load_json


ROBOT_NAME_PREFIX = os.environ.get("ROBOT_NAME_PREFIX", "")


def load_target_robots(path: str, logger: Logger) -> List[Dict[str, Any]]:
    """Load robot account configurations from file.

    Args:
        path: Path to the robot accounts configuration file
        logger: Logger instance

    Returns:
        List of robot account configurations

    Raises:
        FileNotFoundError: If the configuration file does not exist
        json.JSONDecodeError: If the configuration file is not valid JSON
    """
    try:
        return load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(
            "Failed to load robot configuration", extra={"path": path, "error": str(e)}
        )
        raise


def prepare_target_robots(
    target_robots: List[Dict[str, Any]], logger: Logger
) -> List[Tuple[str, Dict[str, Any]]]:
    """Prepare target robots by constructing their full names.

    Args:
        target_robots: List of robot configurations
        logger: Logger instance

    Returns:
        List of tuples containing (full_name, robot_config)

    Raises:
        KeyError: If required fields are missing from robot configuration
    """
    target_robots_with_names = []
    for target_robot in target_robots:
        try:
            full_name = construct_full_robot_name(target_robot)
            target_robots_with_names.append((full_name, target_robot))
        except KeyError as e:
            logger.error(
                "Invalid robot configuration",
                extra={"robot": target_robot, "error": f"Missing field: {str(e)}"},
            )
            raise
    return target_robots_with_names


async def delete_unused_robots(
    client: Any,
    current_robot_map: Dict[str, Any],
    target_robot_names: set,
    logger: Logger,
) -> None:
    """Delete robots that exist in Harbor but not in config.

    Args:
        client: Harbor API client instance
        current_robot_map: Map of current robot names to their configurations
        target_robot_names: Set of robot names from target configuration
        logger: Logger instance

    Raises:
        Exception: If deletion of any robot fails
    """
    for robot_name, robot in current_robot_map.items():
        if robot_name not in target_robot_names:
            try:
                logger.info("Deleting robot not in config", extra={"robot": robot_name})
                await client.delete_robot(robot_id=robot.id)
            except Exception as e:
                logger.error(
                    "Failed to delete robot",
                    extra={"robot": robot_name, "error": str(e)},
                )
                raise


async def process_single_robot(
    client: Any,
    full_name: str,
    target_config: Dict[str, Any],
    current_robot_map: Dict[str, Any],
    logger: Logger,
) -> None:
    """Process a single robot account, either updating existing or creating new.

    Args:
        client: Harbor API client instance
        full_name: Full name of the robot account
        target_config: Robot configuration
        current_robot_map: Map of current robot names to their configurations
        logger: Logger instance

    Raises:
        Exception: If processing of robot configuration fails
    """
    try:
        target_robot = Robot(**target_config)
        target_robot.name = full_name

        if full_name in current_robot_map:
            # Update existing robot
            robot_id = current_robot_map[full_name].id
            logger.info(
                "Updating existing robot",
                extra={"robot": full_name, "robot_id": robot_id},
            )
            await client.update_robot(robot_id=robot_id, robot=target_robot)
            await set_robot_secret(client, target_config, robot_id, logger)
        else:
            # Create new robot
            try:
                logger.info("Creating new robot", extra={"robot": full_name})
                created_robot = await client.create_robot(robot=target_robot)
                await set_robot_secret(client, target_config, created_robot.id, logger)
            except (Conflict, BadRequest) as e:
                logger.error(
                    "Failed to create robot",
                    extra={"robot": full_name, "error": str(e)},
                )
                return

    except Exception as e:
        logger.error(
            "Failed to process robot configuration",
            extra={"robot": full_name, "error": str(e)},
        )
        raise


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
        target_robots = load_target_robots(path, logger)

        # Fetch all existing robots
        try:
            current_robots = await get_all_robots(client, logger)
            current_robot_map = {robot.name: robot for robot in current_robots}
        except Exception as e:
            logger.error("Failed to fetch existing robots", extra={"error": str(e)})
            raise

        # Prepare target robots with full names
        target_robots_with_names = prepare_target_robots(target_robots, logger)
        target_robot_names = {name for name, _ in target_robots_with_names}

        # Delete robots not in config
        await delete_unused_robots(
            client, current_robot_map, target_robot_names, logger
        )

        # Update or create robots
        for full_name, target_config in target_robots_with_names:
            await process_single_robot(
                client, full_name, target_config, current_robot_map, logger
            )

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
    system_robots = await client.get_robots(query="Level=system", limit=None)

    # Get project level robots
    projects = await client.get_projects(limit=None)
    project_robots = []

    for project in projects:
        robots = await client.get_robots(
            query=f"Level=project,ProjectID={project.project_id}", limit=None
        )
        project_robots.extend(robots)

    return system_robots + project_robots


def construct_full_robot_name(target_robot: Dict[str, Any]) -> str:
    """Construct the full robot name including prefix and namespace if applicable.

    Args:
        target_robot: Robot configuration dictionary

    Returns:
        str: Full robot name with prefix and namespace

    Raises:
        KeyError: If required fields are missing from configuration
    """
    namespace = target_robot["permissions"][0]["namespace"]
    robot_name = target_robot["name"]

    if namespace != "*":
        return f"{ROBOT_NAME_PREFIX}{namespace}_{robot_name}"
    return f"{ROBOT_NAME_PREFIX}{robot_name}_


async def set_robot_secret(
    client: Any, target_config: Dict[str, Any], robot_id: int, logger: Logger
) -> None:
    """Set robot account secret from configuration.

    The secret is taken directly from the target configuration's 'secret' field.

    Args:
        client: Harbor API client instance
        target_config: Robot configuration dictionary containing the secret field
        robot_id: Robot account ID
        logger: Logger instance for recording operations
    """
    robot_name = target_config.get("name", "unknown")

    if "secret" not in target_config:
        logger.info(
            "No secret field in robot configuration",
            extra={"robot": robot_name},
        )
        return

    secret = target_config["secret"]

    if secret:
        try:
            logger.info("Setting robot secret", extra={"robot": robot_name})
            await client.refresh_robot_secret(robot_id, secret)
        except Exception as e:
            logger.error(
                "Failed to set robot secret",
                extra={"robot": robot_name, "error": str(e)},
            )
            raise
    else:
        logger.info(
            "Empty secret value in robot configuration",
            extra={"robot": robot_name},
        )
