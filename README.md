## Fabric Commands

### Prepare deploy directory:

```shell
$ fab deploy_setup
```


### Build a revision:

```shell
$ fab build
$ fab build:rev=778af8ebcda621272ae2b0020544c8a6b882d30d
```


### Deploy a revision:

```shell
$ fab deploy  # will prompt for revision
```


### Rollback a version:

```shell
$ fab rollback  # rollback to last version
$ fab rollback:rev=5  # rollback to version 5
```


### Upload a config:

```shell
$ fab upload_config:config=./prod/my_config.conf,dest=my_config.conf
```
