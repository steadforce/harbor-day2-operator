def sync_harbor_configuration():
    # Sync harbor configuration
    print("SYNCING HARBOR CONFIGURATION")
    path = config_folder_path + "/configurations.json"
    if os.path.exists(path):
        harbor_config = json.load(open(path))
        harbor_config = Configurations(**harbor_config)
        harbor_config.oidc_client_secret = oidc_client_secret
        harbor_config.oidc_endpoint = oidc_endpoint
        await sync_harbor_config(harbor_config=harbor_config)
    else:
        print("File configurations.json not found")
        print("Skipping harbor configuration")
    print("")


async def sync_harbor_config(harbor_config: Configurations):
    await client.update_config(harbor_config)
