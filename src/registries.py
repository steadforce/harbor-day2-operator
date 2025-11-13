from typing import Any, Dict, List, Set
from logging import Logger
import json

from utils import load_json


def load_target_registries(path: str, logger: Logger) -> List[Dict[str, Any]]:
    """Load registry configurations from file.

    Args:
        path: Path to the registries configuration file
        logger: Logger instance

    Returns:
        List of registry configurations

    Raises:
        FileNotFoundError: If the configuration file does not exist
        json.JSONDecodeError: If the configuration file is not valid JSON
    """
    try:
        return load_json(path)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(
            "Failed to load registry configuration",
            extra={"path": path, "error": str(e)},
        )
        raise


async def delete_unused_registries(
    client: Any,
    current_registry_map: Dict[str, Any],
    target_registry_names: Set[str],
    logger: Logger,
) -> None:
    """Delete registries that exist in Harbor but not in the config.

    Args:
        client: Harbor API client instance
        current_registry_map: Map of current registry names to their configurations
        target_registry_names: Set of registry names from target configuration
        logger: Logger instance

    Raises:
        Exception: If deletion of any registry fails
    """
    for registry_name, registry in current_registry_map.items():
        if registry_name not in target_registry_names:
            try:
                logger.info(
                    "Deleting registry not in config", extra={"registry": registry_name}
                )
                await client.delete_registry(id=registry.id)
            except Exception as e:
                logger.error(
                    "Failed to delete registry",
                    extra={"registry": registry_name, "error": str(e)},
                )
                raise


async def update_or_create_registries(
    client: Any,
    target_registries: List[Dict[str, Any]],
    current_registry_map: Dict[str, Any],
    logger: Logger,
) -> None:
    """Update existing registries or create new ones based on configuration.

    Args:
        client: Harbor API client instance
        target_registries: List of target registry configurations
        current_registry_map: Map of current registry names to their configurations
        logger: Logger instance

    Raises:
        Exception: If update or creation of any registry fails
    """
    for target_registry in target_registries:
        registry_name = target_registry["name"]
        try:
            if registry_name in current_registry_map:
                logger.info(
                    "Updating existing registry", extra={"registry": registry_name}
                )
                await client.update_registry(
                    id=current_registry_map[registry_name].id, registry=target_registry
                )
                if current_registry_map[registry_name].type != target_registry.type:
                    logger.info("Recreating registry because type has changed", extra={"registry": registry_name})
                    await client.delete_registry(id=current_registry_map[registry_name].id)
                    await client.create_registry(registry=target_registry)
            else:
                logger.info("Creating new registry", extra={"registry": registry_name})
                await client.create_registry(registry=target_registry)
        except Exception as e:
            logger.error(
                "Failed to process registry configuration",
                extra={"registry": registry_name, "error": str(e)},
            )
            raise


async def sync_registries(client: Any, path: str, logger: Logger) -> None:
    """Synchronize Harbor registries with configuration file.

    This function performs the following operations:
    1. Reads registry configurations from the specified file
    2. Deletes registries that exist in Harbor but not in the config
    3. Updates existing registries with new configurations
    4. Creates new registries defined in the config

    Args:
        client: Harbor API client instance
        path: Path to the registries configuration file
        logger: Logger instance for recording operations

    Raises:
        FileNotFoundError: If the configuration file does not exist
        json.JSONDecodeError: If the configuration file is not valid JSON
        Exception: If any Harbor API operation fails
    """
    logger.info("Starting registry synchronization")

    try:
        # Load registry configurations
        target_registries = load_target_registries(path, logger)

        # Get current registries from Harbor
        current_registries = await client.get_registries(limit=None)

        # Create lookup maps for efficient access
        current_registry_map = {reg.name: reg for reg in current_registries}
        target_registry_names = {reg["name"] for reg in target_registries}

        # Delete registries not in config
        await delete_unused_registries(
            client, current_registry_map, target_registry_names, logger
        )

        # Update or create registries from config
        await update_or_create_registries(
            client, target_registries, current_registry_map, logger
        )

        logger.info("Registry synchronization completed successfully")

    except Exception as e:
        logger.error("Registry synchronization failed", extra={"error": str(e)})
        raise
