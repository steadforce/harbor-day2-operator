import json

from utils import fill_template


async def sync_projects(client, path, logger):
    """Synchronize all projects

    All projects from the project file, if existent,
    will be updated and applied to harbor.
    """

    logger.info("Syncing projects")
    target_projects_string = await fill_template(client, path)
    target_projects = json.loads(target_projects_string)
    current_projects = await client.get_projects(limit=None)
    current_project_names = [
        current_project.name for current_project in current_projects
    ]
    target_project_names = [
        target_project["project_name"] for target_project in target_projects
    ]

    # Delete all projects not defined in config file
    for current_project in current_projects:
        if current_project.name not in target_project_names:
            repositories = await client.get_repositories(
                project_name=current_project.name,
                limit=None
            )
            if len(repositories) == 0:
                logger.info(
                    "Deleting project",
                    extra={"project": current_project.name}
                )
                await client.delete_project(
                    project_name_or_id=current_project.name
                )
            else:
                logger.info(
                    "Deletion of project not possible as not empty",
                    extra={"project": current_project.name}
                )

    # Modify existing projects or create new ones
    for target_project in target_projects:
        # Modify existing project
        if target_project["project_name"] in current_project_names:
            logger.info(
                "Syncing project",
                extra={"project": target_project["project_name"]}
            )
            await client.update_project(
                project_name_or_id=current_project.name, project=target_project
            )
        # Create new project
        else:
            logger.info(
                "Creating new project",
                extra={"project": target_project["project_name"]}
            )
            await client.create_project(project=target_project)
