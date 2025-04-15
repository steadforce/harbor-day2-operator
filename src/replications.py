from typing import List, Dict, Any, Set
from logging import Logger
import json

from utils import fill_template


async def load_replication_configs(
    client: Any, path: str, logger: Logger
) -> List[Dict[str, Any]]:
    """Load replication configurations from template file.

    Args:
        client: Harbor API client instance
        path: Path to the replication configuration file
        logger: Logger instance

    Returns:
        List of replication configurations

    Raises:
        FileNotFoundError: If the template file does not exist
        json.JSONDecodeError: If the template content is not valid JSON
    """
    try:
        replications_string = await fill_template(client, path, logger)
        return json.loads(replications_string)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(
            "Failed to load replication configuration",
            extra={"path": path, "error": str(e)},
        )
        raise


async def delete_unused_replications(
    client: Any,
    current_replications: List[Any],
    target_replication_names: Set[str],
    logger: Logger,
) -> None:
    """Delete replication rules that exist in Harbor but not in config.

    Args:
        client: Harbor API client instance
        current_replications: List of current replication rules
        target_replication_names: Set of replication names from target configuration
        logger: Logger instance

    Raises:
        Exception: If deletion of any replication rule fails
    """
    for current_replication in current_replications:
        if current_replication.name not in target_replication_names:
            try:
                logger.info(
                    "Deleting replication rule as it is not defined in config",
                    extra={"replication": current_replication.name},
                )
                await client.delete_replication_policy(policy_id=current_replication.id)
            except Exception as e:
                logger.error(
                    "Failed to delete replication rule",
                    extra={"replication": current_replication.name, "error": str(e)},
                )
                raise


async def process_single_replication(
    client: Any,
    target_replication: Dict[str, Any],
    current_replications: List[Any],
    logger: Logger,
) -> None:
    """Process a single replication rule, either updating existing or creating new.

    Args:
        client: Harbor API client instance
        target_replication: Replication rule configuration
        current_replications: List of current replication rules
        logger: Logger instance

    Raises:
        KeyError: If required fields are missing from replication configuration
        Exception: If any Harbor API operation fails
    """
    try:
        target_replication_name = target_replication["name"]
        current_replication_names = [repl.name for repl in current_replications]

        if target_replication_name in current_replication_names:
            # Update existing replication
            replication_id = current_replications[
                current_replication_names.index(target_replication_name)
            ].id
            logger.info(
                "Updating existing replication rule",
                extra={"replication": target_replication_name},
            )
            await client.update_replication_policy(
                policy_id=replication_id, policy=target_replication
            )
        else:
            # Create new replication
            logger.info(
                "Creating new replication rule",
                extra={"replication": target_replication_name},
            )
            await client.create_replication_policy(policy=target_replication)
    except KeyError as e:
        logger.error(
            "Invalid replication configuration",
            extra={
                "replication": target_replication,
                "error": f"Missing required field: {str(e)}",
            },
        )
        raise
    except Exception as e:
        logger.error(
            "Failed to process replication rule",
            extra={"replication": target_replication_name, "error": str(e)},
        )
        raise


async def sync_replications(client: Any, path: str, logger: Logger) -> None:
    """Synchronize Harbor replication rules with configuration file.

    This function performs the following operations:
    1. Loads replication configurations from template file
    2. Retrieves existing replication rules from Harbor
    3. Deletes rules that exist in Harbor but not in config
    4. Updates existing rules or creates new ones based on config

    Args:
        client: Harbor API client instance
        path: Path to the replication configuration file
        logger: Logger instance for recording operations

    Raises:
        FileNotFoundError: If the configuration file does not exist
        json.JSONDecodeError: If the configuration file is not valid JSON
        KeyError: If required fields are missing in configuration
        Exception: If any Harbor API operation fails
    """
    logger.info("Starting replication rule synchronization")

    try:
        # Load replication configurations
        target_replications = await load_replication_configs(client, path, logger)

        # Get current replications from Harbor
        try:
            current_replications = await client.get_replication_policies()
        except Exception as e:
            logger.error(
                "Failed to fetch existing replications", extra={"error": str(e)}
            )
            raise

        # Create set of target replication names
        target_replication_names = {repl["name"] for repl in target_replications}

        # Delete replications not in config
        await delete_unused_replications(
            client, current_replications, target_replication_names, logger
        )

        # Update or create replications
        for target_replication in target_replications:
            await process_single_replication(
                client, target_replication, current_replications, logger
            )

        logger.info("Replication rule synchronization completed successfully")

    except Exception as e:
        logger.error("Replication rule synchronization failed", extra={"error": str(e)})
        raise
