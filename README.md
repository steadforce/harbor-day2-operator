# harbor-day2-operator
The harbor day2 operator is for automated management of existing harbor instances using python harbor-api

This harbor operator makes it possible to synchronize different types of settings to a harbor instance.
Instead of making changes by hand (clickops), this operator enables the automatic synchronization of harbor settings from files.

The Harbor API of your instance can be found at: `your-harbor-origin/devcenter-api-2.0`

## Requirements

The project uses two requirements files:
- `requirements.txt`: Contains the production dependencies with pinned versions
- `dev_requirements.txt`: Contains development dependencies and base package names

To update the `requirements.txt` file with proper version pinning, use the `create_requirements_in_container.sh` script:

```bash
./create_requirements_in_container.sh
```

This script will:
1. Build a temporary Docker image with the base system dependencies
2. Install all packages from `dev_requirements.txt`
3. Generate a clean `requirements.txt` with exact versions, excluding system packages
4. Preserve any extra index URLs or trusted hosts from `dev_requirements.txt`

Run this script whenever you update dependencies in `dev_requirements.txt` to ensure the `requirements.txt` file stays in sync with proper version pinning.

## Linting

**Code:**
```bash
docker run -v ./src/:/src --pull=always ghcr.io/astral-sh/ruff:latest check /src
docker run -v ./src/:/src --pull=always ghcr.io/astral-sh/ruff:latest check --fix /src
docker run -v ./src/:/src --pull=always ghcr.io/astral-sh/ruff:latest check --fix --unsafe-fixes /src
```

**Dockerfile:**
```bash
 docker run --rm -i ghcr.io/hadolint/hadolint < Dockerfile
```

## Formatting

**Code:**
```bash
docker run -v ./src/:/src --pull=always ghcr.io/astral-sh/ruff:latest format /src
```


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


## Configuration Files

The configuration files are added externally and referenced by the harbor-day2-operator.
The configuration files contain all desired settings in json format.
As ids can change anytime, it is not feasible to keep ids in configuration files.
Instead insert a template for registry and project ids.
The template looks like `{{ registry:name }}` or `{{ project:name }}`,
with name being the name of the project or registry.
The template will be replaced with the actual project or registry id, fetched from the harbor instance.
Note that if there is an entry in the next line the trailing comma is still needed in order to form correct json.
The templating only replaces everything inside and including the double curly braces with the id.

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

### projects.json

A list of projects and their metadata.
Projects can also be used as Proxy Caches.
In that case, they have to refer to the `registry_id` of an existing registry.
Templating can be used to insert the id at runtime.

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
        //"registry_id": 1 -> from template
        "registry_id": "{{ registry:docker.io }}"
    }
]
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
Templating can be used to insert the id of the project at runtime.


```json
[
  {
    "algorithm": "or",
    "scope": {
      "level": "project",
      //"ref": 2 -> from template
      "ref": "{{ project:aa }}"
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
