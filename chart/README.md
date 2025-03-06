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
  adminUsername: "admin"
  robotNamePrefix: "robot$"

oidc:
  endpoint: "https://your-oidc-provider"
  staticClientToken: "your-oidc-client-token"

# Optional: Add custom configuration files
configFiles:
  enabled: true
  "config.yaml": |
    your:
      configuration: here

# Optional: Add custom environment variables
env:
  CUSTOM_VAR:
    value: "direct-value"
  SECRET_VAR:
    valueFrom:
      secretKeyRef:
        name: my-secret
        key: my-key

# Optional: Add custom labels
deployment:
  labels:
    environment: production
  podLabels:
    monitoring: enabled
  selectorLabels:
    tier: backend
```

2. Install the chart:

```bash
helm install harbor-day2-operator ./chart -f values.yaml
```

## Configuration

The following table lists the configurable parameters of the Harbor Day 2 Operator chart and their default values.

| Parameter | Description | Default |
|-----------|-------------|---------|
| `affinity` | Pod affinity settings | `{}` |
| `configFiles.enabled` | Enable configuration files | `true` |
| `configFolder` | Path to configuration files | `/usr/local/scripts` |
| `deployment.labels` | Additional deployment labels | `{}` |
| `deployment.podLabels` | Additional pod labels | `{}` |
| `deployment.selectorLabels` | Additional selector labels | `{}` |
| `env` | Additional environment variables | `{}` |
| `envFrom` | Additional envFrom sources | `[]` |
| `harbor.adminPasswordNew` | New admin password | `"changeme"` |
| `harbor.adminPasswordOld` | Old admin password | `"changeme"` |
| `harbor.adminUsername` | Harbor admin username | `"admin"` |
| `harbor.apiUrl` | Harbor API URL | `""` |
| `harbor.robotNamePrefix` | Prefix for robot accounts | `"robot$"` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `image.repository` | Image repository | `ghcr.io/steadforce/steadops/workbenches/harbor-day2-operator` |
| `image.tag` | Image tag | `""` |
| `nodeSelector` | Node selector settings | `{}` |
| `oidc.endpoint` | OIDC provider endpoint | `""` |
| `oidc.staticClientToken` | OIDC static client token | `"changeme"` |
| `replicaCount` | Number of replicas | `1` |
| `resources` | Container resource requests and limits | See values.yaml |
| `revisionHistoryLimit` | Number of old ReplicaSets to retain | `10` |
| `tolerations` | Pod tolerations | `[]` |

## Environment Variables

The chart supports two ways of defining environment variables:

1. Direct values:
```yaml
env:
  MY_VAR:
    value: "my-value"
```

2. Using valueFrom (for secrets, configmaps, or field refs):
```yaml
env:
  SECRET_VAR:
    valueFrom:
      secretKeyRef:
        name: my-secret
        key: my-key
  CONFIG_VAR:
    valueFrom:
      configMapKeyRef:
        name: my-configmap
        key: my-key
```

## Configuration Files

The operator supports mounting configuration files through the `configFiles` section. Any file type is supported and will be mounted as-is in the container.

Example:
```yaml
configFiles:
  enabled: true
  "config.yaml": |
    settings:
      timeout: 30
      retries: 3
  "script.sh": |
    #!/bin/bash
    echo "Running initialization..."
```

## Custom Labels

The chart allows adding custom labels at different levels:

1. Deployment labels:
```yaml
deployment:
  labels:
    team: myteam
    environment: production
```

2. Pod-specific labels:
```yaml
deployment:
  podLabels:
    monitoring: enabled
```

3. Selector labels (added to both matchLabels and pod labels):
```yaml
deployment:
  selectorLabels:
    tier: backend
```

## Security

The chart creates several Kubernetes secrets to store sensitive information:
- Admin password (new and old)
- OIDC static client token

Make sure to handle these secrets securely and never commit them to version control.
