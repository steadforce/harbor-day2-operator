import json
from utils import fill_template


async def sync_replications(client, path, logger):
    """Synchronize all replication rules

    All replication rules from the replications file will be
    updated and applied to harbor. Existing rules not defined
    in the configuration will be removed.
    """
    logger.info("Syncing replications")

    replications_string = await fill_template(client, path, logger)
    target_replications = json.loads(replications_string)
    current_replications = await client.get_replication_policies()

    current_replication_names = [
        repl.name for repl in current_replications
    ]
    current_replication_ids = [
        repl.id for repl in current_replications
    ]
    target_replication_names = [
        repl["name"] for repl in target_replications
    ]

    # Delete replications not defined in config file
    for current_replication in current_replications:
        if current_replication.name not in target_replication_names:
            logger.info(
                "Deleting replication rule as it is not defined in config",
                extra={"replication": current_replication.name}
            )
            await client.delete_replication_policy(id=current_replication.id)

    # Modify existing replications or create new ones
    for target_replication in target_replications:
        target_replication_name = target_replication["name"]
        if target_replication_name in current_replication_names:
            replication_id = current_replication_ids[
                current_replication_names.index(target_replication_name)
            ]
            logger.info(
                "Syncing replication rule",
                extra={"replication": target_replication_name}
            )
            await client.update_replication_policy(
                id=replication_id,
                policy=target_replication
            )
        else:
            logger.info(
                "Creating new replication rule",
                extra={"replication": target_replication_name}
            )
            await client.create_replication_policy(
                policy=target_replication
            )
