"""Harbor garbage collection schedule management module.

This module handles the synchronization of Harbor garbage collection schedules,
including creation and updates of GC schedules.
"""

import logging

from harborapi.client import HarborAsyncClient
from harborapi.exceptions import HarborAPIException

from .utils import load_json


async def sync_garbage_collection_schedule(
    client: HarborAsyncClient,
    path: str,
    logger: logging.Logger
) -> None:
    """Synchronize the garbage collection schedule with Harbor.

    This function will attempt to update an existing schedule, and if none exists,
    it will create a new one.

    Args:
        client: Harbor API client instance.
        path: Path to the garbage collection schedule JSON file.
        logger: Logger instance for output.

    Raises:
        FileNotFoundError: If the schedule file doesn't exist.
        json.JSONDecodeError: If the schedule file is not valid JSON.
        HarborAPIException: If the Harbor API request fails.
    """
    try:
        logger.info("Loading garbage collection schedule from %s", path)
        schedule_config = load_json(path)

        try:
            # Check if schedule exists
            logger.debug("Checking for existing garbage collection schedule")
            await client.get_gc_schedule()
            
            logger.info("Updating existing garbage collection schedule")
            await client.update_gc_schedule(schedule_config)
            logger.info("Garbage collection schedule updated successfully")
            
        except HarborAPIException as e:
            if hasattr(e, 'status') and e.status == 404:
                logger.info("No existing schedule found, creating new garbage collection schedule")
                await client.create_gc_schedule(schedule_config)
                logger.info("Garbage collection schedule created successfully")
            else:
                raise

    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error("Failed to load garbage collection schedule: %s", str(e))
        raise
    except HarborAPIException as e:
        logger.error("Failed to manage garbage collection schedule: %s", str(e))
        raise
