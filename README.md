# harbor-day2-operator
The harbor day2 operator is for automated management of existing harbor instances using python harbor-api

## Environment Variables
The following environment variables are required:

`ADMIN_USERNAME`  
Username of the administrator account used to login via API. The default is `admin`.

`ADMIN_PASSWORD_OLD`  
The administrator password used previously. If the harbor administrator account password has not yet been updated, both `ADMIN_PASSWORD_OLD` and `ADMIN_PASSWORD_NEW` are required and used to update the admin account password to the `ADMIN_PASSWORD_NEW`.

`ADMIN_PASSWORD_NEW`  
The new administrator password. If the harbor administrator account password has already been updated to the `ADMIN_PASSWORD_NEW` nothing changes.

`HARBOR_API_URL`  
The full Harbor API URL.

`CONFIG_FOLDER_PATH`
The path to the folder containing all configuration files. The files are defined and documented in the harbor repository.

`ROBOT_NAME_PREFIX`  
The prefix used in all robot names.

`OIDC_STATIC_CLIENT_TOKEN`  
The OIDC provider secret.

`OIDC_ENDPOINT`  
The endpoint of the OIDC provider.

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

