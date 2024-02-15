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

