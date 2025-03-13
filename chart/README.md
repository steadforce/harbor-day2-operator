# Harbor Day 2 Operator Helm Chart

This Helm chart deploys the Harbor Day 2 Operator, which is designed for automated management of existing Harbor instances using the Harbor API.

## Prerequisites

- Kubernetes 1.16+
- Helm 3.0+
- An existing Harbor instance
- OIDC provider configuration (if OIDC integration is enabled)
- Kubernetes secrets for sensitive data (admin passwords, robot tokens, OIDC tokens)

## Installing the Chart

1. Create a values file with your configuration:

```yaml
image:
  repository: ghcr.io/steadforce/harbor-day2-operator
  tag: "your-version-tag"
  pullPolicy: IfNotPresent

harbor:
  apiUrl: "https://your-harbor-instance/api/v2.0/"
  adminUsername: "admin"
  newAdminSecretName: "harbor-secrets"  # Name of the secret containing the new admin password
  oldAdminSecretName: "harbor-core"     # Name of the secret containing the old admin password
  robotNamePrefix: "robot$"
  robotSecretName: "harbor-robot-secrets"  # Name of the secret containing robot account tokens

oidc:
  enabled: true  # Set to true to enable OIDC integration
  endpoint: "https://your-oidc-provider"
  secretName: "harbor-oidc-secret"  # Name of the secret containing OIDC client token
  secretKey: "OIDC_STATIC_CLIENT_TOKEN"  # Key in the secret for the OIDC client token

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
| `harbor.adminUsername` | Harbor admin username | `"admin"` |
| `harbor.apiUrl` | Harbor API URL | `""` |
| `harbor.newAdminSecretName` | Name of the secret containing the new admin password | `"harbor-secrets"` |
| `harbor.oldAdminSecretName` | Name of the secret containing the old admin password | `"harbor-core"` |
| `harbor.robotNamePrefix` | Prefix for robot accounts | `"robot$"` |
| `harbor.robotSecretName` | Name of the secret containing robot account tokens | `""` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `image.repository` | Image repository | `ghcr.io/steadforce/harbor-day2-operator` |
| `image.tag` | Image tag | `""` (defaults to chart appVersion) |
| `nodeSelector` | Node selector settings | `{}` |
| `oidc.enabled` | Enable OIDC integration | `false` |
| `oidc.endpoint` | OIDC provider endpoint | `""` |
| `oidc.secretName` | Name of the secret containing OIDC client token | `""` |
| `oidc.secretKey` | Key in the secret for the OIDC client token | `"OIDC_STATIC_CLIENT_TOKEN"` |
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
  FIELD_VAR:
    valueFrom:
      fieldRef:
        fieldPath: metadata.name
```

## Configuration Files

The operator supports mounting configuration files through the `configFiles` section. Any file type is supported and will be mounted as-is in the container at the path specified by `configFolder`.

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

## RBAC

The chart creates the following RBAC resources:
- ServiceAccount: For the Harbor Day 2 Operator
- Role: With permissions to get, list, and watch secrets and configmaps, and to create and patch events
- RoleBinding: Binding the Role to the ServiceAccount

## Security

The chart requires external Kubernetes secrets for all sensitive information. You must create these secrets before deploying the chart:

### Required Secrets

1. **Harbor Admin Passwords**:
   - New admin password in secret specified by `harbor.newAdminSecretName` with key `ADMIN_PASSWORD`
   - Old admin password in secret specified by `harbor.oldAdminSecretName` with key `HARBOR_ADMIN_PASSWORD`

2. **Robot Account Tokens**:
   - Secret specified by `harbor.robotSecretName`
   - Each robot account token should be a key-value pair in the secret
   - Example:
     ```yaml
     apiVersion: v1
     kind: Secret
     metadata:
       name: harbor-robot-secrets
     type: Opaque
     data:
       ROBOT_ACCOUNT_1: <base64-encoded-token>
       ROBOT_ACCOUNT_2: <base64-encoded-token>
     ```

3. **OIDC Client Token** (if OIDC is enabled):
   - Secret specified by `oidc.secretName`
   - Token stored under key specified by `oidc.secretKey`
   - Example:
     ```yaml
     apiVersion: v1
     kind: Secret
     metadata:
       name: harbor-oidc-secret
     type: Opaque
     data:
       OIDC_STATIC_CLIENT_TOKEN: <base64-encoded-token>
     ```

Make sure to handle these secrets securely and never commit them to version control.
