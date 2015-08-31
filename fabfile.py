# vim: set filetype=python:
# coding: utf-8

import os
import tempfile

from fabric.api import (env, local, task, run, sudo, put, cd, get, hosts,
                        parallel, prompt, execute)
from fabric.decorators import runs_once
from fabric.contrib.files import exists

try:
    import fabric_bearychat as bearychat

    env.bearychat_hook = 'BEARYCHAT_HOOK'
except ImportError:
    _i = lambda *args, **kwargs: lambda x: x

    class MockBearychat(object):

        notify_when_finished = _i

    bearychat = MockBearychat()


env.shell = '/bin/bash -l -i -c'
env.use_ssh_config = True

env.roledefs = {
    'staging': [
        'staging@staging.my-server.com',
    ],

    'production': [
        'production@production1.my-server.com',
        'production@production2.my-server.com',
    ],
}


PYTHON = 'python3'

SHARED_FOLDER = 'shared'
RELEASE_FOLDER = 'release'
DEPLOY_FOLDERS = [SHARED_FOLDER, RELEASE_FOLDER]
COUNTER_FILE = 'counter'
KEEP_REVISIONS = 5

# Deploy directory.
env.deploy_to = env.get('deploy_to', '/srv/flaskr.my-server.com')
env.shared_folders = ['log', 'config', 'public']


def deploy_path(*paths):
    return os.path.join(env.deploy_to, *map(str, paths))


def get_deploy_revision_counter():
    count = run('cat {counter}'.format(counter=deploy_path(COUNTER_FILE)))
    return int(count.strip())


def get_next_deploy_revision_counter():
    return get_deploy_revision_counter() + 1


def bump_deploy_revision_counter(to):
    run('echo {to} > {counter_file}'.format(
        to=to,
        counter_file=deploy_path(COUNTER_FILE)
    ))

    old_rev = get_deploy_revision_path(to - KEEP_REVISIONS)
    run('rm -rf {old_rev}'.format(old_rev=old_rev))


def get_deploy_revision_path(rev):
    return deploy_path(RELEASE_FOLDER, rev)


CURRENT_REVISION_PATH = lambda: get_deploy_revision_path('current')


def link_deploy_revision_to_current(rev):
    rev_path = get_deploy_revision_path(rev)
    assert exists(rev_path), 'rev {rev} not exist!'.format(rev=rev_path)
    run('ln -nsf {rev} {current}'.format(
        rev=rev_path,
        current=CURRENT_REVISION_PATH()
    ))


def get_commit_revision(rev):
    rv = local('git rev-parse --short {rev}'.format(rev=rev), capture=True)
    return rv.strip()


def get_package_version():
    return local('python setup.py --version', capture=True).strip()


# FIXME merge with `get_commit_revision`
def get_commit_revision_in_remote(rev):
    rv = run('git rev-parse --short {rev}'.format(rev=rev))
    return rv.strip()


def get_commit_message(rev):
    cmd = 'git log -1 --abbrev-commit --pretty=oneline {rev}'.format(rev=rev)
    rv = local(cmd, capture=True)
    return rv.strip()


def pull_latest_master():
    local('git stash')  # Save local changeset.
    local('git pull origin master')


@task(alias='local')
def vagrant():
    env.user = 'vagrant'
    env.hosts = ['127.0.0.1:2222']
    result = local('vagrant ssh-config | grep IdentityFile', capture=True)
    env.key_filename = result.split()[1]


@task
def deploy_setup():
    '''Prepare deploy environment.'''
    sudo('mkdir -p {deploy_to}'.format(**env))
    run('sudo chown {user} {deploy_to}'.format(**env))

    for folder in DEPLOY_FOLDERS:
        run('mkdir -p {folder_path}'.format(folder_path=deploy_path(folder)))

    for shared_folder in env.shared_folders:
        run('mkdir -p {shared_folder}'.format(
            shared_folder=deploy_path(SHARED_FOLDER, shared_folder)
        ))

    run('echo 0 > {counter}'.format(counter=deploy_path(COUNTER_FILE)))


@task
@runs_once
def deploy():
    revision = prompt('Deploy version, uses HEAD commit by default',
                      default='HEAD')
    env.revision = revision = get_commit_revision(revision)
    env.revision_message = get_commit_message(revision)
    archive = os.path.join(
        'dist',
        'flaskr-{rev}-linux-x86_64.tar.gz'.format(rev=revision)
    )

    execute(do_deploy, archive)


@task
@parallel
@bearychat.notify_when_finished(
    on_succeeded=lambda: '{host} `{revision_message}` deployed'.format(**env),
    on_failed=lambda: '{host} `{revision_message}` is failed'.format(**env)
)
def do_deploy(archive):
    '''Do the deploy job'''
    put(archive, '/tmp/flaskr.tar.gz')
    run('rm -rf /tmp/flaskr && mkdir -p /tmp/flaskr')

    with cd('/tmp/flaskr'):
        run('tar --strip-components=1 -xzf /tmp/flaskr.tar.gz')
        rev = get_next_deploy_revision_counter()
        rev_path = get_deploy_revision_path(rev)

        run('rm -rf {rev_path}'.format(rev_path=rev_path))
        run('./install.sh {rev_path}'.format(rev_path=rev_path))
        link_deploy_revision_to_current(rev)

    run('rm -rf /tmp/flaskr /tmp/flaskr.tar.gz')
    restart()

    bump_deploy_revision_counter(rev)


@task
@bearychat.notify_when_finished(
    on_succeeded=lambda: '{} is rollbacked'.format(env.host),
    on_failed=lambda: '{} rollback is failed'.format(env.host)
)
def rollback(rev=None):
    rev = rev or (get_deploy_revision_counter() - 1)
    link_deploy_revision_to_current(rev)
    restart()


@task
def restart():
    run('supervisorctl restart flaskr:*')


@task
def upload_config(config, dest):
    '''Upload a configuration file.'''
    config = os.path.abspath(config)
    put(config, deploy_path(SHARED_FOLDER, 'config', dest))


@task
@hosts('build@build.my-server.com')
def build(rev=None):
    '''Build a package.'''
    pull_latest_master()
    rev = get_commit_revision(rev or 'HEAD')
    tmp = tempfile.mktemp(suffix='.tar.gz')
    local('git archive "{rev}" | gzip > "{tmp}"'.format(rev=rev, tmp=tmp))

    buildtmp = '/tmp/build-{0}'.format(os.urandom(20).encode('hex'))
    run('mkdir {buildtmp}'.format(buildtmp=buildtmp))
    put(tmp, '{buildtmp}/src.tar.gz'.format(buildtmp=buildtmp))

    buildname = 'flaskr-{rev}-linux-x86_64.tar.gz'.format(rev=rev)
    with cd(buildtmp):
        run('tar xzf src.tar.gz')
        # Write revision to package.
        run('sed -it "s/DEV/{rev}/g" flaskr/__init__.py'.format(rev=rev))

        run(('platter build -p {python}'
             ' -r requirements.txt .').format(python=PYTHON))
        local('mkdir -p dist')
        get('dist/*.tar.gz', 'dist/{buildname}'.format(buildname=buildname))

    run('rm -rf {0}'.format(buildtmp))
