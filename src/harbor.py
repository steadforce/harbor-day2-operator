"""Harbor Day2 Operator main module.

This module is responsible for synchronizing Harbor configurations from JSON files.
It handles various aspects of Harbor configuration including projects, registries,
robot accounts, webhooks, and more.
"""

import os
import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from harborapi import HarborAsyncClient
from pythonjsonlogger import jsonlogger

from src.utils import wait_until_healthy, sync_admin_password
from src.configuration import sync_harbor_configuration
from src.registries import sync_registries
from src.purge_job_schedule import sync_purge_job_schedule
from src.garbage_collection_schedule import sync_garbage_collection_schedule
from src.project_members import sync_project_members
from src.projects import sync_projects
from src.robot_accounts import sync_robot_accounts
from src.webhooks import sync_webhooks
from src.retention_policies import sync_retention_policies


@dataclass
class HarborConfig:
    """Harbor configuration settings."""
    admin_username: str
    admin_password: str
    api_url: str
    config_folder: str
    json_logging: bool

    @classmethod
    def from_env(cls) -> 'HarborConfig':
        """Create configuration from environment variables.

        Returns:
            HarborConfig: Configuration instance

        Raises:
            ValueError: If required environment variables are missing
        """
        admin_password = os.environ.get("ADMIN_PASSWORD_NEW")
        api_url = os.environ.get("HARBOR_API_URL")
        config_folder = os.environ.get("CONFIG_FOLDER_PATH")

        if not all([admin_password, api_url, config_folder]):
            raise ValueError(
                "Missing required environment variables. Please set: "
                "ADMIN_PASSWORD_NEW, HARBOR_API_URL, CONFIG_FOLDER_PATH"
            )

        return cls(
            admin_username=os.environ.get("ADMIN_USERNAME", "admin"),
            admin_password=admin_password,
            api_url=api_url,
            config_folder=config_folder,
            json_logging=os.environ.get("JSON_LOGGING", "").lower() in ["true", "1", "yes", "y"]
        )


def setup_logging(use_json: bool) -> logging.Logger:
    """Configure logging with either JSON or standard format.

    Args:
        use_json: Whether to use JSON logging format

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    formatter = jsonlogger.JsonFormatter() if use_json else logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


class HarborSynchronizer:
    """Handles synchronization of Harbor configurations."""

    def __init__(self, config: HarborConfig, logger: logging.Logger):
        """Initialize the synchronizer.

        Args:
            config: Harbor configuration settings
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.client = HarborAsyncClient(
            url=config.api_url,
            username=config.admin_username,
            secret=config.admin_password,
            timeout=100,
            verify=False,
        )

    async def _sync_config_file(
        self,
        filename: str,
        sync_func: callable,
        required: bool = False
    ) -> None:
        """Synchronize a single configuration file.

        Args:
            filename: Name of the configuration file
            sync_func: Function to call for synchronization
            required: Whether the configuration file is required

        Raises:
            FileNotFoundError: If a required configuration file is missing
        """
        path = Path(self.config.config_folder) / filename

        if not path.exists():
            msg = f"Configuration file not found: {filename}"
            if required:
                self.logger.error(msg)
                raise FileNotFoundError(msg)
            self.logger.info(msg + " - skipping")
            return

        try:
            await sync_func(self.client, str(path), self.logger)
        except Exception as e:
            self.logger.error(
                f"Failed to sync {filename}",
                extra={"error": str(e)}
            )
            raise

    async def synchronize(self) -> None:
        """Synchronize all Harbor configurations.

        This method orchestrates the synchronization of all Harbor components
        in the correct order, ensuring dependencies are met.

        Raises:
            Exception: If any synchronization step fails
        """
        try:
            self.logger.info("Starting Harbor synchronization")

            # Wait for Harbor to be healthy
            self.logger.info("Waiting for Harbor to be healthy")
            await wait_until_healthy(self.client, self.logger)

            # Update admin password if needed
            self.logger.info("Checking admin password")
            await sync_admin_password(self.client, self.logger)

            # Sync configurations in dependency order
            config_files = {
                "configurations.json": sync_harbor_configuration,
                "registries.json": sync_registries,
                "projects.json": sync_projects,
                "project-members.json": sync_project_members,
                "robots.json": sync_robot_accounts,
                "webhooks.json": sync_webhooks,
                "purge-job-schedule.json": sync_purge_job_schedule,
                "garbage-collection-schedule.json": sync_garbage_collection_schedule,
                "retention-policies.json": sync_retention_policies
            }

            for filename, sync_func in config_files.items():
                await self._sync_config_file(filename, sync_func)

            self.logger.info("Harbor synchronization completed successfully")

        except Exception as e:
            self.logger.error(
                "Harbor synchronization failed",
                extra={"error": str(e)}
            )
            raise


async def main() -> None:
    """Main entry point for the Harbor Day2 Operator.

    This function initializes the configuration, sets up logging,
    and runs the synchronization process.

    Raises:
        Exception: If initialization or synchronization fails
    """
    try:
        # Load configuration from environment
        config = HarborConfig.from_env()

        # Setup logging
        logger = setup_logging(config.json_logging)

        # Initialize and run synchronizer
        synchronizer = HarborSynchronizer(config, logger)
        await synchronizer.synchronize()

    except Exception as e:
        logging.error(f"Fatal error: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
