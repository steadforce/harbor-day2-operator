# Harbor Day 2 Operator

![Version: 1.0.0](https://img.shields.io/badge/Version-1.0.0-informational?style=flat-square) ![Type: application](https://img.shields.io/badge/Type-application-informational?style=flat-square) ![AppVersion: 0.0.0](https://img.shields.io/badge/AppVersion-0.0.0-informational?style=flat-square)

This Helm chart deploys the Harbor Day 2 Operator, which is designed for automated management
of existing Harbor instances using the Harbor API.

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
  tag: "my-version-tag"
  pullPolicy: IfNotPresent

harbor:
  apiUrl: "https://my-harbor-instance/api/v2.0/"
  adminUsername: "admin"
  newAdminSecretName: "harbor-secrets"  # Name of the secret containing the new admin password
  oldAdminSecretName: "harbor-core"     # Name of the secret containing the old admin password
  robotNamePrefix: "robot$"
  robotSecretName: "harbor-robot-secrets"  # Name of the secret containing robot account tokens

oidc:
  enabled: true  # Set to true to enable OIDC integration
  endpoint: "https://my-oidc-provider"
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

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| affinity | object | `{}` | Affinity configuration for the operator |
| configFiles | object | `{"enabled":false}` | Configuration files for the operator |
| configFiles.enabled | bool | `false` | Specifies whether configuration files should be mounted |
| configFolder | string | `"/usr/local/scripts"` | Configuration folder for the operator |
| deployment | object | `{"labels":{},"podLabels":{},"selectorLabels":{}}` | Deployment labels for the operator |
| deployment.labels | object | `{}` | Labels to add to the deployment |
| deployment.podLabels | object | `{}` | Labels to add to the pods |
| deployment.selectorLabels | object | `{}` | Labels to add to the selector |
| env | object | `{}` | Environment variables for the operator |
| envFrom | list | `[]` | Environment variables from sources for the operator |
| harbor | object | `{"adminUsername":"admin","apiUrl":"","newAdminSecretName":"harbor-secrets","oldAdminSecretName":"harbor-core","robotNamePrefix":"","robotSecretName":""}` | Harbor configuration |
| harbor.adminUsername | string | `"admin"` | Username for Harbor admin account |
| harbor.apiUrl | string | `""` | URL of the Harbor API endpoint (e.g., https://harbor.example.com/api/v2.0/) |
| harbor.newAdminSecretName | string | `"harbor-secrets"` | Name of the Kubernetes secret containing the new admin password |
| harbor.oldAdminSecretName | string | `"harbor-core"` | Name of the Kubernetes secret containing the old admin password |
| harbor.robotNamePrefix | string | `""` | Prefix for robot account names |
| harbor.robotSecretName | string | `""` | Name of the Kubernetes secret containing robot account tokens |
| image | object | `{"pullPolicy":"IfNotPresent","repository":"ghcr.io/steadforce/harbor-day2-operator","tag":""}` | Image configuration for the operator |
| image.pullPolicy | string | `"IfNotPresent"` | Docker image pull policy (IfNotPresent, Always, or Never) |
| image.repository | string | `"ghcr.io/steadforce/harbor-day2-operator"` | Docker image repository for the operator |
| image.tag | string | `""` | Docker image tag for the operator |
| nodeSelector | object | `{}` | Node selector configuration for the operator |
| oidc | object | `{"enabled":false,"endpoint":"","secretKey":"OIDC_STATIC_CLIENT_TOKEN","secretName":""}` | OIDC configuration |
| oidc.enabled | bool | `false` | Enable or disable OIDC integration for Harbor authentication |
| oidc.endpoint | string | `""` | URL of the OIDC provider endpoint |
| oidc.secretKey | string | `"OIDC_STATIC_CLIENT_TOKEN"` | Key in the secret for the OIDC client token |
| oidc.secretName | string | `""` | Name of the Kubernetes secret containing the OIDC client token |
| podAnnotations | object | `{}` | Pod annotations for the operator |
| podLabels | object | `{}` | Pod labels for the operator |
| replicaCount | int | `1` | Number of replicas for the operator deployment |
| resources | object | `{"limits":{"cpu":"600m","memory":"256Mi"},"requests":{"cpu":"200m","memory":"80Mi"}}` | Resources configuration for the operator |
| resources.limits | object | `{"cpu":"600m","memory":"256Mi"}` | Resource limits for the operator |
| resources.limits.cpu | string | `"600m"` | CPU limit for the operator |
| resources.limits.memory | string | `"256Mi"` | Memory limit for the operator |
| resources.requests | object | `{"cpu":"200m","memory":"80Mi"}` | Resource requests for the operator |
| resources.requests.cpu | string | `"200m"` | CPU request for the operator |
| resources.requests.memory | string | `"80Mi"` | Memory request for the operator |
| tolerations | list | `[]` | Tolerations configuration for the operator |

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

The operator supports mounting configuration files through the `configFiles` section. Any file type is supported and
will be mounted as-is in the container at the path specified by `configFolder`.

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

The chart requires external Kubernetes secrets for all sensitive information.
You must create these secrets before deploying the chart:

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

## Development

The chart can be linted locally with the `chart-testing` tool:

```shell
docker run --pull=always --rm -w /data -v $(pwd):/data quay.io/helmpack/chart-testing ct lint --charts "." --validate-maintainers=false
```

To test the chart locally, you can use the `helm chart-testing` tool helm-unittest:

```shell
docker run --pull=always -ti --rm -v "$(pwd):/apps" -u $(id -u) helmunittest/helm-unittest .
```

Or with output in JUnit format:

```shell
docker run --pull=always -ti --rm -v "$(pwd):/apps" -u $(id -u) helmunittest/helm-unittest -o test-output.xml .
```

Please note that you should **never change** the content of `README.md` as this file will be
automatically generated from `README.md.gotmpl` by the build pipeline.

[helm-docs](https://github.com/norwoodj/helm-docs) is used for auto-generating the documentation from the Helm chart.

For development purposes you can also run the `helm-docs` generator locally in your terminal:

```shell
docker run --pull=always --rm --volume "$(pwd):/helm-docs" -u $(id -u) jnorwood/helm-docs:latest
```

## Build and Publish

Packaging and publishing of new releases will be done via the build pipeline.

In order to create a new release, please create a pull request with an updated version in `Chart.yaml`.
The chart will be published with the new version after the pull request is merged onto the master branch.

----------------------------------------------
Autogenerated from chart metadata using [helm-docs v1.14.2](https://github.com/norwoodj/helm-docs/releases/v1.14.2)
