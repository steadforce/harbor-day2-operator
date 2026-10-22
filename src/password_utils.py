import os
from logging import Logger
from pathlib import Path

from harborapi import HarborAsyncClient
from harborapi.exceptions import Unauthorized

# Environment variables for Harbor configuration
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
API_URL = os.environ.get("HARBOR_API_URL")


def load_new_admin_password() -> str:
    """Load the new admin password from secret path."""
    SECRET_PATH = Path("/etc/secrets/ADMIN_PASSWORD")
    return SECRET_PATH.read_text().strip() if SECRET_PATH.exists() else None


def load_old_admin_password() -> str:
    """Load the old admin password from secret path."""
    SECRET_PATH = Path("/etc/secrets/HARBOR_ADMIN_PASSWORD")
    return SECRET_PATH.read_text().strip() if SECRET_PATH.exists() else None


async def update_password(client: HarborAsyncClient, logger: Logger) -> None:
    """Update the Harbor admin password.

    This function attempts to update the admin password from OLD_ADMIN_PASSWORD
    to NEW_ADMIN_PASSWORD using the provided client.

    Args:
        client: Harbor API client instance
        logger: Logger instance for recording operations

    Raises:
        Unauthorized: If the old password is incorrect
        Exception: If any other error occurs during password update
    """
    try:
        logger.info("Starting admin password update")

        # Create client with old password
        old_password_client = HarborAsyncClient(
            url=API_URL,
            username=ADMIN_USERNAME,
            secret=load_old_admin_password(),
            timeout=10,
            verify=False,
        )

        # Get current user details
        try:
            admin = await old_password_client.get_current_user()
        except Exception as e:
            logger.error("Failed to get current user", extra={"error": str(e)})
            raise

        # Update password
        try:
            await old_password_client.set_user_password(
                user_id=admin.user_id,
                old_password=load_old_admin_password(),
                new_password=load_old_admin_password(),
            )
            logger.info("Admin password updated successfully")
        except Exception as e:
            logger.error("Failed to update password", extra={"error": str(e)})
            raise

    except Unauthorized:
        logger.error("Unable to change admin password: unauthorized")
        raise
    except Exception as e:
        logger.error("Failed to update admin password", extra={"error": str(e)})
        raise


async def sync_admin_password(client: HarborAsyncClient, logger: Logger) -> None:
    """Synchronize admin password if current credentials are invalid.

    This function checks if the current admin credentials are valid and
    updates them if necessary.

    Args:
        client: Harbor API client instance
        logger: Logger instance for recording operations
    """
    try:
        await client.get_current_user()
    except Unauthorized:
        await update_password(client, logger)
    except Exception as e:
        logger.error("Failed to check current user", extra={"error": str(e)})
        raise
