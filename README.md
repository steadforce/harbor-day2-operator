# harbor-day2-operator
The harbor day2 operator is for automated management of existing harbor instances using python harbor-api

## Linter
We have activated linter like hadolint for dockerfiles. Please run
all the linters like documented underneath before checkin of source
code. Pull requests are only accepted when no linting errors occur.

### hadolint

```
 docker run --rm -i ghcr.io/hadolint/hadolint < Dockerfile
```

### python-lint

```
 docker run --rm -v .:/src ricardobchaves6/python-lint-image:1.4.0 pycodestyle /src
```

## Configuration Files

### configurations.json

General configurations including `auth_mode`, `oidc_auto_onboard` and more oidc settings.

```json
{
    "setting": "value"
}
```

### project-members.json

A list of projects and team members with their respective roles.

```json
[
    {
        "project_name": "Project 1",
        "admin": [],
        "developer": [],
        "guest": [],
        "maintainer": []
    }
]
```

### projects.json

A list of projects and metadata.

```json
[
    {
        "project_name": "Project 1",
        "metadata": {
            "public": true,
            "auto_scan": true
        },
        "storage_limit": -1
    }
]
```

### purge-jobs.json

All purge jobs and their schedule.

```json
[
    {
        "paramters": {
            "audit_retention_hour": 720,
            "dry_run": false,
            "include_operations": "create,delete,pull"
        },
        "schedule": {
            "cron": "0 0 0 * * *",
            "type": "daily"
        }
    }
]
```

### registries.json

All information about registries.

```json
[
    {
        "name": "registry.io",
        "url": "https://registry.io",
        "type": "docker-registry",
        "description": "Example docker registry."
    }
]
```

### robots.json

Configuration of robot accounts and their permissions.

```json
[
    {
        "name": "example-robot",
        "duration": "-1",
        "description": "Example robot.",
        "disable": false,
        "level": "system",
        "permissions": [
            {
                "kind": "project",
                "namespace": "*",
                "access": [
                    {
                        "resource": "repository",
                        "action": "list"
                    }
                ]
            }
        ]
    }
]
```

### webhooks.json

Definition of webhooks.

```json
[
    {
        "project_name": "Project 1", 
        "policies": [
            "name": "ms-teams",
            "description": "Sends scan results to MS-Teams",
            "event_types": [
                "SCANNING_COMPLETED"
            ],
            "targets": [
                {
                    "type": "http",
                    "address": "https://harbor-ms-teams-forwarder.url.com"
                }
            ],
            "enabled": true
        ]
    }
]
```

