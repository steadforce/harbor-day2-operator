def sync_garbage_collection_schedule():
    # Sync garbage collection schedule
    print("SYNCING GARBAGE COLLECTION SCHEDULE")
    path = config_folder_path + "/garbage-collection-schedule.json"
    if os.path.exists(path):
        garbage_collection_config = json.load(open(path))
        await sync_garbage_collection_schedule(
            garbage_collection_schedule=garbage_collection_config
        )
    else:
        print("File garbage-collection-schedule.json not found")
        print("Skipping syncing garbage collection schedule")
    print("")


async def sync_garbage_collection_schedule(
    garbage_collection_schedule: Schedule
) -> None:
    try:
        await client.get_gc_schedule()
        print("Updating garbage collection schedule")
        await client.update_gc_schedule(garbage_collection_schedule)
    except Exception as e:
        print("Creating garbage collection schedule")
        await client.create_gc_schedule(garbage_collection_schedule)
