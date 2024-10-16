def sync_project_members():
    # Sync project members and their roles
    print("SYNCING PROJECT MEMBERS")
    path = config_folder_path + "/project-members.json"
    if os.path.exists(path):
        project_members_config = json.load(open(path))
        for project in project_members_config:
            await sync_project_members(project=project)
    else:
        print("File project-members.json not found")
        print("Skipping syncing project members")
    print("")


async def sync_project_members(project) -> None:
    project_name = project["project_name"]
    print(f'PROJECT: "{project_name}"')

    current_members = await client.get_project_members(
        project_name_or_id=project_name,
        limit=None
    )
    target_members = []
    for project_role in ProjectRole:
        target_members += [
            ProjectMemberEntity(
                entity_name=username, role_id=project_role.value
            )
            for username in project[project_role.name.lower()]
        ]

    # Remove all non listed current project members
    for current_member in current_members:
        if current_member.entity_name not in [
            target_member.entity_name for target_member in target_members
        ]:
            print(
                f'- Removing "{current_member.entity_name}" from project'
                f' "{project_name}"'
            )
            await client.remove_project_member(
                project_name_or_id=project_name,
                member_id=current_member.id,
            )

    # Update existing members and add new ones
    for member in target_members:
        member_id = get_member_id(current_members, member.entity_name)
        # Sync existing members' project role
        if member_id:
            print(f'- Syncing project role of "{member.entity_name}"')
            await client.update_project_member_role(
                project_name_or_id=project_name,
                member_id=member_id,
                role=member.role_id,
            )
        # Add new member
        else:
            print(
                f'- Adding new member "{member.entity_name}" to project'
                f' "{project_name}"'
            )
            try:
                await client.add_project_member_user(
                    project_name_or_id=project_name,
                    username_or_id=member.entity_name,
                    role_id=member.role_id,
                )
            except NotFound:
                print(
                    f'  => ERROR: User "{member.entity_name}" not found. Make'
                    " sure the user has logged into harbor at least once"
                )
