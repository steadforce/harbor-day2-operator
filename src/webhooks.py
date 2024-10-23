from harborapi.models import WebhookPolicy
import json


async def sync_webhooks(client, path):
    """Synchronize all webhooks

    All webhooks from the webhooks file, if existent,
    will be updated and applied to harbor.
    """

    print("SYNCING WEBHOOKS")
    webhooks_config = json.load(open(path))
    for webhook in webhooks_config:
        await sync_webhook(client, **webhook)


async def sync_webhook(
    client, project_name: str, policies: list[WebhookPolicy]
):
    print(f'PROJECT: "{project_name}"')

    target_policies = policies
    current_policies = await client.get_webhook_policies(
        project_name_or_id=project_name,
        limit=None
    )
    current_policy_names = [
        current_policy.name for current_policy in current_policies
    ]
    current_policy_id = [
        current_policy.id for current_policy in current_policies
    ]
    target_policy_names = [
        target_policy["name"] for target_policy in target_policies
    ]

    # Delete all policies not defined in config file
    for current_policy in current_policies:
        if current_policy.name not in target_policy_names:
            print(
                f'- Deleting policy "{current_policy.name}" since it is not'
                " defined in config files"
            )
            await client.delete_webhook_policy(
                project_name_or_id=project_name,
                webhook_policy_id=current_policy.id,
            )

    # Modify existing policies or create new ones
    for target_policy in target_policies:
        # Modify existing policy
        if target_policy["name"] in current_policy_names:
            policy_id = current_policy_id[
                current_policy_names.index(target_policy["name"])
            ]
            print(f'- Syncing policy "{target_policy["name"]}"')
            await client.update_webhook_policy(
                project_name_or_id=project_name,
                webhook_policy_id=policy_id,
                policy=target_policy,
            )
        # Create new policy
        else:
            print(f'- Creating new policy "{target_policy["name"]}"')
            await client.create_webhook_policy(
                project_name_or_id=project_name, policy=target_policy
            )
