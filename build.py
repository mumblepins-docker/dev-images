#!/usr/bin/env python

import datetime
import os
import re
import shutil
import sys
import tempfile
import unicodedata
from contextlib import contextmanager
from shlex import split as shsplit
from subprocess import check_output, PIPE, Popen
from timeit import default_timer as timer

from config import *

save_dir = os.path.abspath(save_dir)

fill_in_copy = {}
for k, v in fill_in_data.items():
    fill_in_copy[os.path.abspath(k)] = v
fill_in_data = fill_in_copy
del fill_in_copy


@contextmanager
def cd(newdir):
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)


def del_empty_dirs():
    for root, dirs, files in os.walk(".", topdown=False):
        root = os.path.abspath(root)
        for d in dirs:
            fpath = os.path.join(root, d)
            # print fpath
            dir_list = os.listdir(fpath)
            if dir_list == ['Dockerfile'] or len(dir_list) == 0:
                print "Deleting {}".format(fpath)
                dirs.remove(d)
                shutil.rmtree(fpath)


def file_fill_in(file_in, file_fill, starter='### Build-time metadata ###'):
    with open(file_in, 'r') as fhi:
        in_lines = fhi.readlines()
    with open(file_fill, 'r') as fhf:
        fill_in = fhf.readlines()
    with open(file_in, 'w') as fhi:
        for line in in_lines:
            fhi.write(line)
            if starter in line:
                fhi.writelines(fill_in)


def splitall(path):
    """
    https://www.safaribooksonline.com/library/view/python-cookbook/0596001673/ch04s16.html
    Args:
        path:

    Returns:

    """
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path:  # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    return allparts


def create_dir(path, includes):
    tdir = tempfile.mkdtemp()
    lastname = os.path.basename(path)
    tdirmain = os.path.join(tdir, lastname)
    shutil.copytree(path, tdirmain)
    for p in includes:
        shutil.copytree(p, os.path.join(tdirmain, os.path.basename(p)))
    for k, v in fill_in_data.items():
        file_fill_in(os.path.join(tdirmain, 'Dockerfile'), k, v)
    with cd(tdirmain):
        del_empty_dirs()
    return tdir, tdirmain


def init_env(tag):
    deploy = True
    git_commit = check_output(shsplit('git rev-parse --short HEAD')).strip()
    git_url = check_output(shsplit('git config --get remote.origin.url')).strip()
    if 'git@github.com' in git_url:
        git_url = re.sub('git@github.com', 'https://github.com', git_url)
    git_branch = check_output(shsplit('git rev-parse --abbrev-ref HEAD')).strip()
    if git_branch != 'master':
        tag += '_{}'.format(git_commit)
        deploy = False

    build_date = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
    date = datetime.datetime.utcnow().strftime('%Y%m%d')
    env = dict(
        GIT_COMMIT=git_commit,
        GIT_URL=git_url,
        GIT_BRANCH=git_branch,
        BUILD_DATE=build_date,
        VERSION=tag,
        DOCKER_IMAGE=DOCKER_IMAGE,
        DATE=date
    )
    env['FULL_IMAGE_NAME'] = '{DOCKER_IMAGE}:{VERSION}'.format(**env)
    return env, deploy


def build_image(path, env):
    print "Building {FULL_IMAGE_NAME}".format(**env)

    with cd(path):
        cmd = 'docker build \
              --build-arg BUILD_DATE="{BUILD_DATE}" \
              --build-arg VERSION="{VERSION}" \
              --build-arg VCS_URL="{GIT_URL}" \
              --build-arg VCS_REF="{GIT_COMMIT}" \
              -t {DOCKER_IMAGE}:{VERSION} .'.format(**env)
        run_command(cmd)
        # process = Popen(cmd, stdout=PIPE)
        # for line in iter(process.stdout.readline, ''):
        #     sys.stdout.write(line)


def save_image(save_dir, env):
    print "Saving {FULL_IMAGE_NAME}".format(**env)
    filename = unicodedata.normalize('NFKD', env['FULL_IMAGE_NAME'].decode('UTF-8')).encode('ascii', 'ignore')
    filename = unicode(re.sub('[^\w\s-]', '', filename).strip().lower())
    filename = unicode(re.sub('[-\s]+', '-', filename) + '.tar.lz4')
    print check_output(shsplit('mkdir -p {}'.format(save_dir)))
    env['SAVE_NAME'] = filename
    with cd(save_dir):
        cmd = 'docker save {DOCKER_IMAGE}:{VERSION} | lz4 -zc > {SAVE_NAME}'.format(**env)
        print cmd
        start = timer()
        print check_output(cmd, shell=True)
        end = timer()
        print "Elapsed Time: {:0.3f}s".format(end - start)


def in_multi(string):
    for part in ignore_lines:
        if part in string:
            return True
    return False


def run_command(string, echo=True, quiet=False):
    cmd = shsplit(string)
    if echo:
        print cmd
    process = Popen(cmd, stdout=PIPE)
    for line in iter(process.stdout.readline, ''):
        if not quiet:
            if not in_multi(line):
                sys.stdout.write(line)


def deploy_image(env):
    if latest == env['VERSION']:
        run_command('docker tag {DOCKER_IMAGE}:{VERSION} {DOCKER_IMAGE}:latest'.format(**env))
    run_command('docker tag {DOCKER_IMAGE}:{VERSION} {DOCKER_IMAGE}:{VERSION}-{DATE}'.format(**env))
    print run_command('docker push {DOCKER_IMAGE}:{VERSION}'.format(**env))


print "Logging in..."
print check_output(shsplit('docker login -u {DOCKER_USER} -p {DOCKER_PASS}'.format(**os.environ)))

for root, dirs, files in os.walk(".", topdown=False):
    root = re.sub(r'^\./', '', root)
    fullpath = splitall(root)
    if fullpath[0].startswith('.'):
        continue
    if fullpath[0] in include_dirs:
        continue
    if 'Dockerfile' not in files:
        continue

    tag_name = '-'.join(fullpath)

    abspath = os.path.abspath(root)
    incpaths = [os.path.abspath(a) for a in include_dirs]

    tempdir, workdir = create_dir(abspath, incpaths)

    env, deploy = init_env(tag_name)
    build_image(workdir, env)

    save_image(save_dir, env)

    if deploy:
        deploy_image(env)
    print "Deleting temp directory {}".format(tempdir)
    shutil.rmtree(tempdir)

