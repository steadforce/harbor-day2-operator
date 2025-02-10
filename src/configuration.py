"""Harbor configuration management module.

This module handles the synchronization of Harbor configuration settings,
including OIDC authentication parameters.
"""

import logging
import os

from harborapi.client import HarborAsyncClient
from harborapi.models import Configurations
from harborapi.exceptions import HarborAPIException

from .utils import load_json


async def sync_harbor_configuration(
    client: HarborAsyncClient,
    path: str,
    logger: logging.Logger
) -> None:
    """Synchronize the Harbor configuration from a JSON file.

    Args:
        client: Harbor API client instance.
        path: Path to the configuration JSON file.
        logger: Logger instance for output.

    Raises:
        FileNotFoundError: If the configuration file doesn't exist.
        json.JSONDecodeError: If the configuration file is not valid JSON.
        HarborAPIException: If the Harbor API request fails.
        KeyError: If required environment variables are missing.
    """
    try:
        logger.info("Loading Harbor configuration from %s", path)
        config_data = load_json(path)
        
        # Get required OIDC configuration
        harbor_config = Configurations(**config_data)
        harbor_config.oidc_client_secret = os.environ["OIDC_STATIC_CLIENT_TOKEN"]
        harbor_config.oidc_endpoint = os.environ["OIDC_ENDPOINT"]
        
        logger.info("Updating Harbor configuration")
        await client.update_config(harbor_config)
        logger.info("Harbor configuration updated successfully")
        
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error("Failed to load configuration: %s", str(e))
        raise
    except KeyError as e:
        logger.error("Missing required environment variable: %s", str(e))
        raise
    except HarborAPIException as e:
        logger.error("Failed to update Harbor configuration: %s", str(e))
        raise
