async def sync_garbage_collection_schedule():
    """Synchronize the garbage collection and its schedule

    The garbage collection and its schedule from the garbage collection
    schedule file, if existent, will be updated and applied to harbor.
    """

    print("SYNCING GARBAGE COLLECTION SCHEDULE")
    path = config_folder_path + "/garbage-collection-schedule.json"
    garbage_collection_schedule = json.load(open(path))
    try:
        await client.get_gc_schedule()
        print("Updating garbage collection schedule")
        await client.update_gc_schedule(garbage_collection_schedule)
    except Exception as e:
        print("Creating garbage collection schedule")
        await client.create_gc_schedule(garbage_collection_schedule)
