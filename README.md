## Workflow

1. Bootstrap the deploy environment:

  ```shell
  $ fab deploy_setup
  ```

2. Development & test at local.

3. Commit your changes.

4. Build the package at build machine:

  ```shell
  $ fab build:rev=HEAD
  ```

5. Deploy the package:

  ```shell
  $ fab deploy
  ```

6. Check production version.

7. (If production failed) rollback a version:

  ```shell
  $ fab rollback
  ```

8. Goto step 2.


## Tools

- [fabric][], required in local.
- [platter][], required in build machine.

[fabric]: http://fabric.readthedocs.org
[platter]: http://platter.pocoo.org/dev/


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
