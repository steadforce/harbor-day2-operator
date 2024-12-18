import json


async def sync_registries(client, path, logger):
    """Synchronize all registries

    All registries from the registries file, if existent,
    will be updated and applied to harbor.
    """

    logger.info("Syncing registries")
    target_registries = json.load(open(path))
    current_registries = await client.get_registries(limit=None)
    current_registry_names = [
        current_registry.name for current_registry in current_registries
    ]
    current_registry_id = [
        current_registry.id for current_registry in current_registries
    ]
    target_registry_names = [
        target_registry["name"] for target_registry in target_registries
    ]

    # Delete all registries not defined in config file
    for current_registry in current_registries:
        if current_registry.name not in target_registry_names:
            logger.info(
                "Deleting registry as it is not defined in config",
                extra={"registry": current_registry.name}
            )
            await client.delete_registry(id=current_registry.id)

    # Modify existing registries or create new ones
    for target_registry in target_registries:
        # Modify existing registry
        target_registry_name = target_registry["name"]
        if target_registry_name in current_registry_names:
            registry_id = current_registry_id[
                current_registry_names.index(target_registry_name)
            ]
            logger.info(
                "Syncing registy",
                extra={"registry": target_registry_name}
            )
            await client.update_registry(
                id=registry_id, registry=target_registry
            )
        # Create new registry
        else:
            logger.info(
                "Creating new registry",
                extra={"registry": target_registry_name}
            )
            await client.create_registry(registry=target_registry)
