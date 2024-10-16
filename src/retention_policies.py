def sync_retention_policies():
    # Sync retention policies
    print('SYNCING RETENTION POLICIES')
    path = config_folder_path + "/retention-policies.json"
    if os.path.exists(path):
        retention_policies_config = json.load(open(path))
        await sync_retention_policies(
            retention_policies=retention_policies_config
        )
    else:
        print("File retention-policies.json not found")
        print("Skipping syncing retention policies")


async def sync_retention_policies(retention_policies: [RetentionPolicy]):
    for retention_policy in retention_policies:
        retention_scope = retention_policy["scope"]["ref"]
        try:
            project_retention_id = await client.get_project_retention_id(
                retention_scope
            )
            await client.update_retention_policy(
                project_retention_id,
                retention_policy
            )
            print(f"Updating retention policy for project with id "
                  f"{retention_scope}")
        except Exception as e:
            print(f"Creating retention policy for project with id "
                  f"{retention_scope}")
            await client.create_retention_policy(
                retention_policy
            )
