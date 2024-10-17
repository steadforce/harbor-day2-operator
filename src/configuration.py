import json
from harborapi.models import Configurations


async def sync_harbor_configuration(client, path):
    """Synchronize the harbor configuration

    The configurations file, if existent, will be applied to harbor.
    """

    print("SYNCING HARBOR CONFIGURATION")
    harbor_config = json.load(open(path))
    harbor_config = Configurations(**harbor_config)
    harbor_config.oidc_client_secret = oidc_client_secret
    harbor_config.oidc_endpoint = oidc_endpoint
    await client.update_config(harbor_config)
