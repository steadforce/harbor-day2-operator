from typing import Any, Dict, List
from logging import Logger

from utils import load_json


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
        try:
            target_registries: List[Dict[str, Any]] = load_json(path)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(
                "Failed to load registry configuration",
                extra={"path": path, "error": str(e)}
            )
            raise

        # Get current registries from Harbor
        current_registries = await client.get_registries(limit=None)
        
        # Create lookup maps for efficient access
        current_registry_map = {
            reg.name: reg for reg in current_registries
        }
        target_registry_names = {
            reg["name"] for reg in target_registries
        }

        # Delete registries not in config
        for registry_name, registry in current_registry_map.items():
            if registry_name not in target_registry_names:
                try:
                    logger.info(
                        "Deleting registry not in config",
                        extra={"registry": registry_name}
                    )
                    await client.delete_registry(id=registry.id)
                except Exception as e:
                    logger.error(
                        "Failed to delete registry",
                        extra={"registry": registry_name, "error": str(e)}
                    )
                    raise

        # Update or create registries from config
        for target_registry in target_registries:
            registry_name = target_registry["name"]
            try:
                if registry_name in current_registry_map:
                    # Update existing registry
                    logger.info(
                        "Updating existing registry",
                        extra={"registry": registry_name}
                    )
                    await client.update_registry(
                        id=current_registry_map[registry_name].id,
                        registry=target_registry
                    )
                else:
                    # Create new registry
                    logger.info(
                        "Creating new registry",
                        extra={"registry": registry_name}
                    )
                    await client.create_registry(registry=target_registry)
            except Exception as e:
                logger.error(
                    "Failed to process registry configuration",
                    extra={"registry": registry_name, "error": str(e)}
                )
                raise

        logger.info("Registry synchronization completed successfully")

    except Exception as e:
        logger.error("Registry synchronization failed", extra={"error": str(e)})
        raise
