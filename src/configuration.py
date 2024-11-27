import json
import os
from harborapi.models import Configurations


oidc_client_secret = os.environ.get("OIDC_STATIC_CLIENT_TOKEN")
oidc_endpoint = os.environ.get("OIDC_ENDPOINT")


async def sync_harbor_configuration(client, path, logger):
    """Synchronize the harbor configuration

    The configurations file, if existent, will be applied to harbor.
    """

    logger.info("Syncing harbor configuration")
    harbor_config = json.load(open(path))
    harbor_config = Configurations(**harbor_config)
    harbor_config.oidc_client_secret = oidc_client_secret
    harbor_config.oidc_endpoint = oidc_endpoint
    await client.update_config(harbor_config)
