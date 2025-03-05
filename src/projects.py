import json
from typing import List, Dict, Any, Set
from logging import Logger

from utils import fill_template


async def load_target_projects(client: Any, path: str, logger: Logger) -> List[Dict[str, Any]]:
    """Load and parse the target project configuration.

    Args:
        client: Harbor API client instance
        path: Path to the project configuration file
        logger: Logger instance

    Returns:
        List of project configurations

    Raises:
        json.JSONDecodeError: If project configuration file is not valid JSON
    """
    target_projects_string = await fill_template(client, path, logger)
    return json.loads(target_projects_string)

async def delete_unused_projects(
    client: Any,
    current_projects: Dict[str, Any],
    target_project_names: Set[str],
    logger: Logger
) -> None:
    """Delete projects that are not in the target configuration if they are empty.

    Args:
        client: Harbor API client instance
        current_projects: Map of current project names to their configurations
        target_project_names: Set of project names from target configuration
        logger: Logger instance
    """
    for project_name, _ in current_projects.items():
        if project_name not in target_project_names:
            try:
                repositories = await client.get_repositories(
                    project_name=project_name,
                    limit=None
                )
                
                if not repositories:
                    logger.info(
                        "Deleting project",
                        extra={"project": project_name}
                    )
                    await client.delete_project(project_name_or_id=project_name)
                else:
                    logger.warning(
                        "Cannot delete non-empty project",
                        extra={"project": project_name, "repo_count": len(repositories)}
                    )
            except Exception as e:
                logger.error(
                    "Failed to process project deletion",
                    extra={"project": project_name, "error": str(e)}
                )

async def update_or_create_projects(
    client: Any,
    target_projects: List[Dict[str, Any]],
    current_project_map: Dict[str, Any],
    logger: Logger
) -> None:
    """Update existing projects or create new ones based on target configuration.

    Args:
        client: Harbor API client instance
        target_projects: List of target project configurations
        current_project_map: Map of current project names to their configurations
        logger: Logger instance
    """
    for target_project in target_projects:
        project_name = target_project["project_name"]
        try:
            if project_name in current_project_map:
                logger.info(
                    "Updating existing project",
                    extra={"project": project_name}
                )
                await client.update_project(
                    project_name_or_id=project_name,
                    project=target_project
                )
            else:
                logger.info(
                    "Creating new project",
                    extra={"project": project_name}
                )
                await client.create_project(project=target_project)
        except Exception as e:
            logger.error(
                "Failed to process project configuration",
                extra={"project": project_name, "error": str(e)}
            )

async def sync_projects(client: Any, path: str, logger: Logger) -> None:
    """Synchronize Harbor projects based on configuration file.

    This function performs the following operations:
    1. Reads and parses the project configuration file
    2. Retrieves current projects from Harbor
    3. Deletes projects that are not in the config (if they are empty)
    4. Updates existing projects or creates new ones based on config

    Args:
        client: Harbor API client instance
        path: Path to the project configuration file
        logger: Logger instance for recording operations

    Raises:
        json.JSONDecodeError: If project configuration file is not valid JSON
        Exception: If any Harbor API operation fails
    """
    logger.info("Starting project synchronization")
    
    try:
        # Load target project configuration
        target_projects = await load_target_projects(client, path, logger)
        
        # Get current projects from Harbor
        current_projects = await client.get_projects(limit=None)
        current_project_map = {proj.name: proj for proj in current_projects}
        target_project_names = {proj["project_name"] for proj in target_projects}

        # Delete projects not in config if they're empty
        await delete_unused_projects(client, current_project_map, target_project_names, logger)

        # Update or create projects from config
        await update_or_create_projects(client, target_projects, current_project_map, logger)
                
    except json.JSONDecodeError as e:
        logger.error("Invalid project configuration JSON", extra={"error": str(e)})
        raise
    except Exception as e:
        logger.error("Project synchronization failed", extra={"error": str(e)})
        raise

    logger.info("Project synchronization completed")
