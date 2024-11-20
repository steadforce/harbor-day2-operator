import json


async def sync_purge_job_schedule(client, path, logger):
    """Synchronize the purge job and its schedule

    The purge job and its schedule from the purge job schedule file,
    if existent, will be updated and applied to harbor.
    """

    logger.info("Syncing purge job schedule")
    purge_job_schedule = json.load(open(path))
    try:
        await client.get_purge_job_schedule()
        logger.info("Updating purge job schedule")
        await client.update_purge_job_schedule(purge_job_schedule)
    except Exception as e:
        logger.info("Creating purge job schedule")
        await client.create_purge_job_schedule(purge_job_schedule)
