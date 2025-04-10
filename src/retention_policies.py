import json
from typing import Any, Dict, List
from logging import Logger

from utils import fill_template


async def load_retention_policies(client: Any, path: str, logger: Logger) -> List[Dict[str, Any]]:
    """Load and parse retention policies from template file.

    Args:
        client: Harbor API client instance
        path: Path to the retention policies template file
        logger: Logger instance

    Returns:
        List of retention policy configurations

    Raises:
        FileNotFoundError: If the template file does not exist
        json.JSONDecodeError: If the template content is not valid JSON
    """
    try:
        retention_policies_string = await fill_template(client, path, logger)
        return json.loads(retention_policies_string)
    except FileNotFoundError as e:
        logger.error(
            "Retention policy template file not found",
            extra={"path": path, "error": str(e)}
        )
        raise
    except json.JSONDecodeError as e:
        logger.error(
            "Invalid JSON in retention policy template",
            extra={"path": path, "error": str(e)}
        )
        raise

async def process_single_policy(
    client: Any,
    policy: Dict[str, Any],
    logger: Logger
) -> None:
    """Process a single retention policy, either updating existing or creating new.

    Args:
        client: Harbor API client instance
        policy: Retention policy configuration
        logger: Logger instance

    Raises:
        KeyError: If required fields are missing from policy configuration
        Exception: If any Harbor API operation fails
    """
    try:
        project_id = policy["scope"]["ref"]
        
        try:
            # Try to update existing policy
            retention_id = await client.get_project_retention_id(project_id)
            logger.info(
                "Updating existing retention policy",
                extra={
                    "project_id": project_id,
                    "retention_id": retention_id
                }
            )
            await client.update_retention_policy(retention_id, policy)
        
        except Exception as e:
            if "not found" in str(e).lower():
                # Create new policy if one doesn't exist
                logger.info(
                    "Creating new retention policy",
                    extra={"project_id": project_id}
                )
                await client.create_retention_policy(policy)
            else:
                # Re-raise unexpected errors
                logger.error(
                    "Failed to get retention policy ID",
                    extra={
                        "project_id": project_id,
                        "error": str(e)
                    }
                )
                raise
                
    except KeyError as e:
        logger.error(
            "Invalid retention policy configuration",
            extra={
                "policy": policy,
                "error": f"Missing required field: {str(e)}"
            }
        )
        raise
    except Exception as e:
        logger.error(
            "Failed to process retention policy",
            extra={
                "project_id": project_id,
                "error": str(e)
            }
        )
        raise

async def sync_retention_policies(client: Any, path: str, logger: Logger) -> None:
    """Synchronize Harbor retention policies with configuration file.

    This function reads retention policies from a template file and either updates
    existing policies or creates new ones in Harbor. The template file can contain
    project references that will be resolved using the fill_template utility.

    Args:
        client: Harbor API client instance
        path: Path to the retention policies template file
        logger: Logger instance for recording operations

    Raises:
        FileNotFoundError: If the template file does not exist
        json.JSONDecodeError: If the template content is not valid JSON
        Exception: If any Harbor API operation fails
    """
    logger.info("Starting retention policy synchronization")

    try:
        # Load and parse retention policies from template
        retention_policies = await load_retention_policies(client, path, logger)

        # Process each retention policy
        for policy in retention_policies:
            await process_single_policy(client, policy, logger)

        logger.info("Retention policy synchronization completed successfully")

    except Exception as e:
        logger.error("Retention policy synchronization failed", extra={"error": str(e)})
        raise
