# harbor-day2-operator
The harbor day2 operator is for automated management of existing harbor instances using python harbor-api

This harbor operator makes it possible to synchronize different types of settings to a harbor instance.
Instead of making changes by hand (clickops), this operator enables the automatic synchronization of harbor settings from files.

The Harbor API of your instance can be found at: `your-harbor-origin/devcenter-api-2.0`

## Requirements

The project uses these requirements files:
- `requirements.txt`: Contains the production dependencies with pinned versions
- `dev_requirements.txt`: Contains development dependencies and base package names

`build_requirements.txt` pins the build tools of the image (pip, setuptools, wheel, pyinstaller); Renovate proposes updates for it like for the other requirements files.

`test_requirements.txt` holds the test tools (pytest) and is not part of the image: the script below generates
`requirements.txt` from `dev_requirements.txt`, so test tools do not belong there. The unit tests run in CI before the image build and locally with:

```bash
pip install -r requirements.txt -r test_requirements.txt
python -m pytest tests
```

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
|`ADMIN_USERNAME`|required (defaults to `admin` if not given)|admin|Username of the administrator account used to log in via API. The default is `admin`.|
|`ADMIN_PASSWORD_OLD`|not required|***|The administrator password used previously. If the harbor administrator account password has not yet been updated, both `ADMIN_PASSWORD_OLD` and `ADMIN_PASSWORD_NEW` are required and used to update the admin account password to the `ADMIN_PASSWORD_NEW`.|
|`ADMIN_PASSWORD_NEW`|required|***|The new administrator password. If the harbor administrator account password has already been updated to the `ADMIN_PASSWORD_NEW` nothing changes.|
|`HARBOR_API_URL`|required|https://harbor.domain.com/api/v2.0/|The full Harbor API URL.|
|`CONFIG_FOLDER_PATH`|required|/usr/local/scripts|The path to the folder containing all configuration files. The files are defined and documented in the harbor repository. The path depends on how the `harbor-day2-operator` is deployed.|
|`ROBOT_NAME_PREFIX`|not required|(empty)|The prefix used in all robot names.|
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

If credentials are needed:

  ```json
  [
    {
      "name": "docker.io",
      "url": "https://index.docker.io/v1/",
      "type": "docker-registry",
      "description": "Docker Hub registry.",
      "credential": {
        "access_key": "${REGISTRY_USERNAME}",
        "access_secret": "${REGISTRY_PASSWORD}",
        "type": "basic"
      }
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
        "registry_id": {{ registry:docker.io }}
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

Robot names and secrets can be templated using environment variables in the format `${VARIABLE_NAME}`.
The `secret` field is optional - if provided, it should reference an environment variable containing the robot's secret.

```json
[
    {
        "name": "${ROBOT_AGENT_USER}",
        "secret": "${ROBOT_AGENT_USER_PW}",
        "duration": "-1",
        "description": "Example robot with templated name and secret.",
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
    },
    {
        "name": "static-robot",
        "duration": "-1",
        "description": "Example robot with static name and no secret.",
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
        "include_event_types": "create,delete,pull"
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
      "ref": {{ project:aa }}
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

### replications.json

Definition of replication rules between Harbor instances or external registries.
Replication rules can be found in the global settings under the "Replications" tab.
The rules define how artifacts are replicated between registries, including filters and triggers.

**Note:** `src_registry` and `dest_registry` can't be used together.
The replication is always from `src_registry` to this harbor instance or from this harbor instance to `dest_registry`.
See [Harbor Issue 10272](https://github.com/goharbor/harbor/issues/10272)

**From SRC to this harbor:**
```json
[
    {
        "name": "example-replication",
        "description": "Example replication rule",
        "src_registry": {
            "id": {{ registry:source-registry }}
        },
        "dest_namespace": "replicated-project",
        "filters": [
            {
                "type": "name",
                "value": "**"
            },
            {
                "type": "tag",
                "value": "latest"
            }
        ],
        "trigger": {
            "type": "manual"
        },
        "deletion": false,
        "override": true,
        "enabled": true
    }
]
```

**From this harbor to DEST:**
```json
[
    {
        "name": "example-replication",
        "description": "Example replication rule",
        "dest_registry": {
            "id": {{ registry:destination-registry }}
        },
        "dest_namespace": "replicated-project",
        "filters": [
            {
                "type": "name",
                "value": "**"
            },
            {
                "type": "tag",
                "value": "latest"
            }
        ],
        "trigger": {
            "type": "manual"
        },
        "deletion": false,
        "override": true,
        "enabled": true
    }
]
```

## Testing Workflows with Act

This repository includes configuration for testing GitHub Actions workflows locally using [Act](https://github.com/nektos/act).

### Prerequisites

- [Act](https://github.com/nektos/act) installed (available in the Steadforce k8s workbench)
- Docker running on your machine

### Running Tests

To test the Helm chart publishing workflow:

```bash
# Run the workflow with the provided event.json
act release
```

This will execute the workflow using the simulated release event in `.github/workflows/event.json`.

### Configuration

The workflow is configured to be Act-friendly:

- `.actrc` file contains configuration to set required environment variables and specify the event file
- `event.json` simulates a GitHub release event with the `act: true` property to skip the publish job
- The publish job in the workflow has a condition to skip when running with Act
- The upload-artifact step is skipped when running with Act due to limitations with the ACTIONS_RUNTIME_TOKEN

### Limitations

When testing with Act, some GitHub Actions features are not fully supported:

1. The `actions/upload-artifact` and `actions/download-artifact` actions require an `ACTIONS_RUNTIME_TOKEN` which Act doesn't provide
2. Some GitHub context variables may not be available or may have different values
3. Secrets handling is limited

## Releases and tags

A release is created by publishing a GitHub release whose tag is a plain semantic version without a `v` prefix (for example `1.2.3`).
Publishing the release builds the image (`1.2.3`, `1.2`, `1`) and publishes the Helm chart. Pushing a tag alone does not start a build,
so a release builds exactly once.

The release notes are generated by GitHub from the merged pull requests since the previous release and grouped by label as configured in
[`.github/release.yaml`](.github/release.yaml): Renovate pull requests carry the label `dependencies` and are listed under "Dependency
updates", everything else under "Other changes". Label a pull request `skip-changelog` to leave it out.

### Nightly patch release

[`nightly-patch-release.yaml`](.github/workflows/nightly-patch-release.yaml) runs every night (02:17 UTC) and can be started by hand
(`workflow_dispatch`, with `dry_run` on by default: it only reports in the run summary what it would release).
If one of `requirements.txt`, `dev_requirements.txt`, `build_requirements.txt` or `Dockerfile` changed since the newest stable tag
(`x.y.z`, prereleases such as `1.1.1-test4` are ignored), it releases the next patch version from the head of `main`:
it builds and pushes the image and the Helm chart (the two workflows are called with the version), then creates the tag and the
GitHub release with generated notes. Changes of `src/`, `tests/`, `chart/` and `.github/` do not trigger a release, but a dependency
release contains them if they were merged since the last release. Minor and major releases stay manual: publish a GitHub release
by hand, the next nightly run continues from its tag. The result (published or failed) is posted to the Teams release channel
(secret `STEADOPS_RELEASE_MS_TEAMS_WEBHOOK`).

A manually published GitHub release (for example a minor release `1.3.0`, tag without `v`, target `main`) builds the image and the chart
in the same way and posts one card per result, "Image <tag> published/failed" and "Chart <tag> published/failed", to the same channel.

### Image scanning and signing

Every image that is pushed (releases, `main` and branch builds) is scanned and signed; pull request images are not pushed.

- **Trivy scan before the push:** the image is built once, scanned, and only pushed when the scan passes. The build fails on `HIGH` and `CRITICAL`
  vulnerabilities that already have a fixed version (`ignore-unfixed`). Pull requests are only reported, so the update that fixes a finding
  can still be merged. A finding that has to be accepted goes into `.trivyignore` with a comment and an expiry date (`CVE-... exp:2026-12-31`).
  The Python libraries are bundled inside the PyInstaller binary, which Trivy cannot look into, so a second scan covers the builder stage, where they are
  installed with all their dependencies (the build tools pip, setuptools, wheel and pyinstaller are skipped because they are not shipped). The same gate applies.
  Only libraries are scanned there (the build-only OS packages are not shipped; the OS packages of the published image are scanned by the first scan).
  Limit: the builder stage contains every installed library, also ones that PyInstaller may not bundle.
- **Cosign keyless signature:** after the push the image digest is signed with the identity of the workflow (GitHub OIDC, recorded in the
  public Rekor log) and the signature is verified in the same run. There is no key or secret to manage.
- **Pinned scan tools:** `trivy-action` and `cosign-installer` are pinned to commit SHAs (most `trivy-action` tags were rewritten to
  malicious commits in March 2026); Renovate keeps the SHAs and the version comments up to date.
  The Trivy version itself is set once in `SCANNER_TRIVY_VERSION` at the top of the build workflow and used by all four Trivy steps; Renovate
  updates it (a custom regex manager in `renovate.json`) three days after release and merges it when the checks pass (a malicious Trivy
  release was published in March 2026, hence the wait).

Verify an image before using it:

```bash
cosign verify \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  --certificate-identity-regexp '^https://github\.com/steadforce/harbor-day2-operator/\.github/workflows/build-and-publish-container-image\.yaml@' \
  ghcr.io/steadforce/harbor-day2-operator:1.3.0
```

### SBOM

Every pushed image gets a CycloneDX SBOM (JSON). It lists the operating system packages of the image and the Python libraries, which are
bundled inside the PyInstaller binary (taken from the builder stage, build tools excluded; merged by
[`.github/sbom/merge_sbom.py`](.github/sbom/merge_sbom.py)).

- **Signed attestation on the image:** attached to the image digest with `cosign attest` (keyless, same identity as the image signature) and
  verified in the same run. Download and verify it:

  ```bash
  cosign verify-attestation --type cyclonedx \
    --certificate-oidc-issuer https://token.actions.githubusercontent.com \
    --certificate-identity-regexp '^https://github\.com/steadforce/harbor-day2-operator/\.github/workflows/build-and-publish-container-image\.yaml@' \
    ghcr.io/steadforce/harbor-day2-operator:1.3.0 | jq -r '.payload | @base64d | fromjson | .predicate' > sbom.cdx.json
  ```

- **Asset of the GitHub release:** `harbor-day2-operator-<version>.cdx.json` is attached to every release (nightly and manual).
- **Build artifact:** the file `sbom` of the workflow run for 90 days (releases, `main` and branch builds).
- Scan it later for new vulnerabilities: `trivy sbom sbom.cdx.json`.
