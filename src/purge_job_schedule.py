async def sync_purge_job_schedule():
    """Synchronize the purge job and its schedule

    The purge job and its schedule from the purge job schedule file, if existent, will be updated and applied to harbor.
    """

    print("SYNCING PURGE JOB SCHEDULE")
    path = config_folder_path + "/purge-job-schedule.json"
    purge_job_schedule = json.load(open(path))
    try:
        await client.get_purge_job_schedule()
        print("Updating purge job schedule")
        await client.update_purge_job_schedule(purge_job_schedule)
    except Exception as e:
        print("Creating purge job schedule")
        await client.create_purge_job_schedule(purge_job_schedule)
