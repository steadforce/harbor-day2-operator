import json


async def sync_retention_policies(client, path):
    """Synchronize the retention policies

    The retention policies from the retention policies file, if existent,
    will be updated and applied to harbor.
    """

    print('SYNCING RETENTION POLICIES')
    retention_policies_string = await fill_template(client, path)
    retention_policies = json.load(retention_policies_string)
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
