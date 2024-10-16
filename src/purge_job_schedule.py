def sync_purge_job_schedule():
    # Sync purge job schedule
    print("SYNCING PURGE JOB SCHEDULE")
    path = config_folder_path + "/purge-job-schedule.json"
    if os.path.exists(path):
        purge_jobs_config = json.load(open(path))
        await sync_purge_job_schedule(purge_job_schedule=purge_jobs_config)
    else:
        print("File purge-job-schedule.json not found")
        print("Skipping syncing purge job schedule")
    print("")


async def sync_purge_job_schedule(purge_job_schedule: Schedule) -> None:
    try:
        await client.get_purge_job_schedule()
        print("Updating purge job schedule")
        await client.update_purge_job_schedule(purge_job_schedule)
    except Exception as e:
        print("Creating purge job schedule")
        await client.create_purge_job_schedule(purge_job_schedule)
