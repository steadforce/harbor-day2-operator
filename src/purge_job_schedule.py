import json
from typing import Any, Dict
from logging import Logger

from utils import load_json


async def sync_purge_job_schedule(client: Any, path: str, logger: Logger) -> None:
    """Synchronize the Harbor purge job schedule configuration.

    This function reads the purge job schedule configuration from a file and
    either updates an existing schedule or creates a new one in Harbor.

    Args:
        client: Harbor API client instance
        path: Path to the purge job schedule configuration file
        logger: Logger instance for recording operations

    Raises:
        FileNotFoundError: If the configuration file does not exist
        json.JSONDecodeError: If the configuration file is not valid JSON
        Exception: If any Harbor API operation fails
    """
    logger.info("Starting purge job schedule synchronization")

    try:
        # Load configuration using utility function
        try:
            purge_job_schedule: Dict[str, Any] = load_json(path)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(
                "Failed to load purge job schedule configuration",
                extra={"path": path, "error": str(e)},
            )
            raise

        # Try to update existing schedule, create new one if it doesn't exist
        try:
            await client.get_purge_job_schedule()
            logger.info(
                "Updating existing purge job schedule",
                extra={"schedule": purge_job_schedule},
            )
            await client.update_purge_job_schedule(purge_job_schedule)
        except Exception as e:
            if "not found" in str(e).lower():
                logger.info(
                    "Creating new purge job schedule",
                    extra={"schedule": purge_job_schedule},
                )
                await client.create_purge_job_schedule(purge_job_schedule)
            else:
                logger.error(
                    "Failed to manage purge job schedule", extra={"error": str(e)}
                )
                raise

        logger.info("Purge job schedule synchronization completed successfully")

    except Exception as e:
        logger.error(
            "Purge job schedule synchronization failed", extra={"error": str(e)}
        )
        raise
