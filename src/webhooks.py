from typing import List, Dict, Any, Set
from logging import Logger
import json

from utils import load_json


def load_webhook_configs(path: str, logger: Logger) -> List[Dict[str, Any]]:
    """Load webhook configurations from file.

    Args:
        path: Path to the webhooks configuration file
        logger: Logger instance

    Returns:
        List of webhook configurations

    Raises:
        FileNotFoundError: If the configuration file does not exist
        json.JSONDecodeError: If the configuration file is not valid JSON
    """
    try:
        return load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(
            "Failed to load webhook configuration",
            extra={"path": path, "error": str(e)},
        )
        raise


async def delete_unused_policies(
    client: Any,
    project_name: str,
    current_policy_map: Dict[str, Any],
    target_policy_names: Set[str],
    logger: Logger,
) -> None:
    """Delete webhook policies that exist in Harbor but not in config.

    Args:
        client: Harbor API client instance
        project_name: Name of the project
        current_policy_map: Map of current policy names to their configurations
        target_policy_names: Set of policy names from target configuration
        logger: Logger instance

    Raises:
        Exception: If deletion of any policy fails
    """
    for policy_name, policy in current_policy_map.items():
        if policy_name not in target_policy_names:
            try:
                logger.info(
                    "Deleting webhook policy not in config",
                    extra={"project": project_name, "policy": policy_name},
                )
                await client.delete_webhook_policy(
                    project_name_or_id=project_name, webhook_policy_id=policy.id
                )
            except Exception as e:
                logger.error(
                    "Failed to delete webhook policy",
                    extra={
                        "project": project_name,
                        "policy": policy_name,
                        "error": str(e),
                    },
                )
                raise


async def process_single_policy(
    client: Any,
    project_name: str,
    target_policy: Dict[str, Any],
    current_policy_map: Dict[str, Any],
    logger: Logger,
) -> None:
    """Process a single webhook policy, either updating existing or creating new.

    Args:
        client: Harbor API client instance
        project_name: Name of the project
        target_policy: Webhook policy configuration
        current_policy_map: Map of current policy names to their configurations
        logger: Logger instance

    Raises:
        KeyError: If required fields are missing from policy configuration
        Exception: If any Harbor API operation fails
    """
    try:
        policy_name = target_policy["name"]

        if policy_name in current_policy_map:
            # Update existing policy
            policy_id = current_policy_map[policy_name].id
            logger.info(
                "Updating existing webhook policy",
                extra={
                    "project": project_name,
                    "policy": policy_name,
                    "policy_id": policy_id,
                },
            )
            await client.update_webhook_policy(
                project_name_or_id=project_name,
                webhook_policy_id=policy_id,
                policy=target_policy,
            )
        else:
            # Create new policy
            logger.info(
                "Creating new webhook policy",
                extra={"project": project_name, "policy": policy_name},
            )
            await client.create_webhook_policy(
                project_name_or_id=project_name, policy=target_policy
            )
    except KeyError as e:
        logger.error(
            "Invalid webhook policy configuration",
            extra={
                "project": project_name,
                "policy": target_policy,
                "error": f"Missing required field: {str(e)}",
            },
        )
        raise
    except Exception as e:
        logger.error(
            "Failed to process webhook policy",
            extra={"project": project_name, "policy": policy_name, "error": str(e)},
        )
        raise


async def sync_webhook(
    client: Any, logger: Logger, project_name: str, policies: List[Dict[str, Any]]
) -> None:
    """Synchronize webhook policies for a specific project.

    This function performs the following operations:
    1. Retrieves existing webhook policies for the project
    2. Deletes policies that exist in Harbor but not in config
    3. Updates existing policies or creates new ones

    Args:
        client: Harbor API client instance
        logger: Logger instance for recording operations
        project_name: Name of the project to sync webhooks for
        policies: List of webhook policy configurations

    Raises:
        Exception: If any Harbor API operation fails
    """
    logger.info("Synchronizing webhooks for project", extra={"project": project_name})

    try:
        # Get current policies
        current_policies = await client.get_webhook_policies(
            project_name_or_id=project_name, limit=None
        )

        # Create lookup maps for efficient access
        current_policy_map = {policy.name: policy for policy in current_policies}
        target_policy_names = {policy["name"] for policy in policies}

        # Delete policies not in config
        await delete_unused_policies(
            client, project_name, current_policy_map, target_policy_names, logger
        )

        # Update or create policies
        for target_policy in policies:
            await process_single_policy(
                client, project_name, target_policy, current_policy_map, logger
            )

    except Exception as e:
        logger.error(
            "Failed to sync webhooks for project",
            extra={"project": project_name, "error": str(e)},
        )
        raise


async def sync_webhooks(client: Any, path: str, logger: Logger) -> None:
    """Synchronize Harbor webhooks with configuration file.

    This function reads webhook configurations from a file and synchronizes
    them with Harbor by project. For each project, it will manage webhook
    policies according to the configuration.

    Args:
        client: Harbor API client instance
        path: Path to the webhooks configuration file
        logger: Logger instance for recording operations

    Raises:
        FileNotFoundError: If the configuration file does not exist
        json.JSONDecodeError: If the configuration file is not valid JSON
        KeyError: If required fields are missing in configuration
        Exception: If any Harbor API operation fails
    """
    logger.info("Starting webhook synchronization")

    try:
        # Load webhook configurations
        webhook_configs = load_webhook_configs(path, logger)

        # Process webhooks for each project
        for config in webhook_configs:
            try:
                await sync_webhook(client, logger, **config)
            except Exception as e:
                logger.error(
                    "Failed to sync webhooks for project",
                    extra={
                        "project": config.get("project_name", "unknown"),
                        "error": str(e),
                    },
                )
                raise

        logger.info("Webhook synchronization completed successfully")

    except Exception as e:
        logger.error("Webhook synchronization failed", extra={"error": str(e)})
        raise
