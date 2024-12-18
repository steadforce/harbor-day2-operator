# Harbor Day 2 Operator Helm Chart

This Helm chart deploys the Harbor Day 2 Operator, which is designed for automated management of existing Harbor instances using the Harbor API.

## Prerequisites

- Kubernetes 1.16+
- Helm 3.0+
- An existing Harbor instance
- OIDC provider configuration

## Installing the Chart

1. Create a values file with your configuration:

```yaml
image:
  tag: "your-version-tag"

harbor:
  apiUrl: "https://your-harbor-instance/api/v2.0/"
  adminPasswordNew: "your-new-admin-password"
  adminPasswordOld: "your-old-admin-password"  # Optional
  robotSecrets: {}  # Add your robot account secrets

oidc:
  endpoint: "https://your-oidc-provider"
  staticClientToken: "your-oidc-client-token"

configFiles:
  enabled: true
  # Add your configuration files here
  "config.json": |
    {
      "your": "configuration"
    }
```

2. Install the chart:

```bash
helm install harbor-day2-operator ./harbor-day2-operator -f values.yaml
```

## Configuration

The following table lists the configurable parameters of the Harbor Day 2 Operator chart and their default values.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of replicas | `1` |
| `image.repository` | Image repository | `ghcr.io/steadforce/steadops/workbenches/harbor-day2-operator` |
| `image.tag` | Image tag | `""` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `harbor.apiUrl` | Harbor API URL | `""` |
| `harbor.adminUsername` | Harbor admin username | `"admin"` |
| `harbor.adminPasswordNew` | New admin password | `""` |
| `harbor.adminPasswordOld` | Old admin password | `""` |
| `harbor.robotNamePrefix` | Prefix for robot accounts | `"robot$"` |
| `oidc.endpoint` | OIDC provider endpoint | `""` |
| `oidc.staticClientToken` | OIDC static client token | `""` |
| `configFolder` | Path to configuration files | `/usr/local/scripts` |
| `configFiles.enabled` | Enable configuration files | `true` |

## Configuration Files

The operator uses configuration files in JSON format to define the desired state of the Harbor instance. These files should be provided through the `configFiles` section in the values.yaml.

Example configuration:

```yaml
configFiles:
  enabled: true
  "projects.json": |
    {
      "projects": [
        {
          "name": "example-project",
          "public": false
        }
      ]
    }
  "robots.json": |
    [
      {
        "name": "example-robot",
        "duration": "-1",
        "description": "Example robot"
      }
    ]
```

## Security

The chart creates several Kubernetes secrets to store sensitive information:
- Admin password (new and old)
- Robot account credentials
- OIDC static client token

Make sure to handle these secrets securely and never commit them to version control.
