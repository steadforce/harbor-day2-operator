def sync_projects():
    # Sync projects
    print("SYNCING PROJECTS")
    path = config_folder_path + "/projects.json"
    if os.path.exists(path):
        projects_config = json.load(open(path))
        await sync_projects(target_projects=projects_config)
    else:
        print("File projects.json not found")
        print("Skipping syncing projects")
    print("")


async def sync_projects(target_projects: [Project]) -> None:
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
                print(
                    f'- Deleting project "{current_project.name}" since it is'
                    " empty and not defined in config files"
                )
                await client.delete_project(
                    project_name_or_id=current_project.name
                )
            else:
                print(
                    f'- Deletion of project "{current_project.name}" not'
                    " possible since it is not empty"
                )

    # Modify existing projects or create new ones
    for target_project in target_projects:
        # Modify existing project
        if target_project["project_name"] in current_project_names:
            print(f'- Syncing project "{target_project["project_name"]}"')
            await client.update_project(
                project_name_or_id=current_project.name, project=target_project
            )
        # Create new project
        else:
            print(f'- Creating new project "{target_project["project_name"]}"')
            await client.create_project(project=target_project)
