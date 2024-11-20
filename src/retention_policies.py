import json


async def sync_retention_policies(client, path, logger):
    """Synchronize the retention policies

    The retention policies from the retention policies file, if existent,
    will be updated and applied to harbor.
    """

    logger.info("Syncing retention policies")
    retention_policies = json.load(open(path))
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
            logger.info(
                "Updating retention policy",
                extra={"project_id": retention_scope}
            )
        except Exception as e:
            logger.info(
                "Creating retention policy",
                extra={"project_id": retention_scope}
            )
            await client.create_retention_policy(
                retention_policy
            )
