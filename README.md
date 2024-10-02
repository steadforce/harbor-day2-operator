# harbor-day2-operator
The harbor day2 operator is for automated management of existing harbor instances using python harbor-api

## Environment Variables
The following environment variables are expected:

|Environment Variable|Required|Example Value|Explanation|
|-------|-------|--------|-------|
|`ADMIN_USERNAME`|required (defaults to `admin` if not given)|admin|Username of the administrator account used to login via API. The default is `admin`.|
|`ADMIN_PASSWORD_OLD`|not required|***|The administrator password used previously. If the harbor administrator account password has not yet been updated, both `ADMIN_PASSWORD_OLD` and `ADMIN_PASSWORD_NEW` are required and used to update the admin account password to the `ADMIN_PASSWORD_NEW`.|
|`ADMIN_PASSWORD_NEW`|required|***|The new administrator password. If the harbor administrator account password has already been updated to the `ADMIN_PASSWORD_NEW` nothing changes.|
|`HARBOR_API_URL`|required|https://harbor.domain.com/api/v2.0/|The full Harbor API URL.|
|`CONFIG_FOLDER_PATH`|required|/usr/local/scripts|The path to the folder containing all configuration files. The files are defined and documented in the harbor repository. The path depends on how the `harbor-day2-operator` is deployed.|
|`ROBOT_NAME_PREFIX`|not required|robot$|The prefix used in all robot names.|
|`OIDC_STATIC_CLIENT_TOKEN`|required|***|The OIDC provider secret.|
|`OIDC_ENDPOINT`|required|https://oidc.domain.com/api|The endpoint of the OIDC provider.|


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

The configuration files are added externally and referenced by the harbor-day2-operator. The configuration files contain all desired settings in json format.

### configurations.json

General configurations for auth and oidc.

```json
{
    "auth_mode": "oidc_auth",
    "oidc_auto_onboard": true,
    "oidc_client_id": "harbor",
    "oidc_client_secret": "OVERWRITTEN_BY_ENV_VARIABLE",
    "oidc_endpoint": "OVERWRITTEN_BY_ENV_VARIABLE",
    "oidc_groups_claim": "group",
    "oidc_name": "harbor",
    "oidc_scope": "openid,offline_access,email,groups,profile",
    "oidc_user_claim": "preferred_username",
    "oidc_verify_cert": false
}
```

### project-members.json

A list of projects and team members with their respective roles.

```json
[
    {
        "project_name": "Project 1",
        "admin": [],
        "developer": ["firstname.lastname"],
        "guest": [],
        "maintainer": []
    }
]
```

### projects.json

A list of projects and their metadata.
Projects can also be used as Proxy Caches. In that case, they have to refer to the `registry_id` of an existing registry.
The `registry_id` can be found in the registry definitions in the `registries.json` file.

```json
[
    {
        "project_name": "Project 1",
        "metadata": {
            "public": true,
            "auto_scan": true
        },
        "storage_limit": -1
    },
    {
        "project_name": "Proxy Cache",
        "metadata": {
            "public": "true",
            "auto_scan": "false"
        },
        "storage_limit": -1,
        "registry_id": 1
    }
]
```

### purge-job-schedule.json

The schedule of the purge job, there can always only be one.
The purge job schedule can be found in the page "Clean Up" under the tab "Log Rotation".

```json
{
    "parameters": {
        "audit_retention_hour": 720,
        "dry_run": false,
        "include_operations": "create,delete,pull"
    },
    "schedule": {
        "cron": "0 53 0 * * *",
        "type": "Custom"
    }
}
```

### garbage-collection-schedule.json

The schedule of the garbage collection, there can always only be one.
The garbage collection schedule can be found in the page "Clean Up" under the tab "Garbage Collection".

```json
{
    "parameters": {
        "delete_untagged": true,
        "workers": 1
    },
    "schedule": {
        "cron": "0 47 0 * * *",
        "type": "Custom"
    }
}
```

### retention-policies.json

Definition of the retention policies.
The retention policies can be set per project.
They can be found in each project page under the tab Policy.
`scope.ref` refers to the `project_id` (integer) this retention policy should be associated with.
This `project_id` can be found in the url of each project. For example:
`Project 1` has the url `https://harbor-url.com/harbor/projects/`**`2`**`/repositories`. That means the `project_id` of `Project 1` is `2`.


```json
[
  {
    "algorithm": "or",
    "scope": {
      "level": "project",
      "ref": 2
    },
    "rules": [
      {
	"action": "retain",
        "template": "always",
        "tag_selectors": [
          {
            "decoration": "matches",
	    "kind": "doublestar",
            "pattern": "**"
          }
        ],
        "scope_selectors":  {
          "repository": [
            {
              "decoration": "repoMatches",
              "kind": "doublestar",
              "pattern": "**"
            }
          ]
        }
      }
    ],
    "trigger": {
      "kind": "Schedule",
      "settings": {
        "cron": "0 43 0 * * *"
      }
    }
  }
]
```

### registries.json

All information about registries.
All registries have an `id`, whether implicitly or explicitly set.

```json
[
    {
        "name": "registry.io",
        "id": 1,
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

