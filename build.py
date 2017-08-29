#!/usr/bin/env python

import datetime
import os
import re
import shutil
import sys
import tempfile
import unicodedata
from contextlib import contextmanager
from pprint import pprint
from shlex import split as shsplit
from subprocess import check_output, PIPE, Popen
from timeit import default_timer as timer

from config import DockerConfig

@contextmanager
def cd(newdir):
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)


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


def in_multi(string, in_lines):
    for part in in_lines:
        if part in string:
            return True
    return False


class DockerBuild(object):
    def __init__(self, path):
        pathparts = splitall(path)
        self.base_tag = '-'.join(pathparts)
        self.base_path = os.path.abspath(path)
        self.__dict__.update(DockerConfig.values())

        self.include_dirs = [os.path.abspath(a) for a in self.include_dirs]
        self.deploy = True

        self.env = None

        self.create_dir()
        self.init_env()

    def create_dir(self):
        self.tempdir = tempfile.mkdtemp()
        lastname = os.path.basename(self.base_path)
        self.workdir = os.path.join(self.tempdir, lastname)
        shutil.copytree(self.base_path, self.workdir)
        for p in self.include_dirs:
            shutil.copytree(p, os.path.join(self.workdir, os.path.basename(p)))
        for k, v in self.fill_in_data.items():
            self.file_fill_in(os.path.abspath(k), v)
        with cd(self.workdir):
            self.del_empty_dirs()

    def init_env(self):
        git_commit = check_output(shsplit('git rev-parse --short HEAD')).strip()
        git_url = check_output(shsplit('git config --get remote.origin.url')).strip()
        if 'git@github.com' in git_url:
            git_url = re.sub('git@github.com', 'https://github.com', git_url)
        git_branch = check_output(shsplit('git rev-parse --abbrev-ref HEAD')).strip()
        if git_branch != 'master':
            self.base_tag += '_{}'.format(git_commit)
            self.deploy = False

        build_date = datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z'
        date = datetime.datetime.utcnow().strftime('%Y%m%d')
        self.env = dict(
            GIT_COMMIT=git_commit,
            GIT_URL=git_url,
            GIT_BRANCH=git_branch,
            BUILD_DATE=build_date,
            VERSION=self.base_tag,
            DOCKER_IMAGE=self.DOCKER_IMAGE,
            DATE=date
        )
        self.env['FULL_IMAGE_NAME'] = '{DOCKER_IMAGE}:{VERSION}'.format(**self.env)

    def build_image(self):
        print "Building {FULL_IMAGE_NAME}".format(**self.env)

        with cd(self.workdir):
            cmd = 'docker build \
                  --build-arg BUILD_DATE="{BUILD_DATE}" \
                  --build-arg VERSION="{VERSION}" \
                  --build-arg VCS_URL="{GIT_URL}" \
                  --build-arg VCS_REF="{GIT_COMMIT}" \
                  -t {DOCKER_IMAGE}:{VERSION} .'.format(**self.env)
            self.run_command(cmd)

    def run_command(self, string, echo=True, quiet=False, dry_run=False):
        cmd = shsplit(string)
        if echo:
            if dry_run:
                print "Dry run: {}".format(cmd)
            else:
                print "Running: {}".format(cmd)
        if dry_run:
            return
        process = Popen(cmd, stdout=PIPE)
        for line in iter(process.stdout.readline, ''):
            if not quiet:
                if not in_multi(line, self.ignore_lines):
                    sys.stdout.write(line)

    @staticmethod
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

    def file_fill_in(self, file_fill, starter):
        d_file = os.path.join(self.workdir, 'Dockerfile')
        with open(d_file, 'r') as fhi:
            in_lines = fhi.readlines()
        with open(file_fill, 'r') as fhf:
            fill_in = fhf.readlines()
        with open(d_file, 'w') as fhi:
            for line in in_lines:
                fhi.write(line)
                if starter in line:
                    fhi.writelines(fill_in)

    def save_image(self):
        save_dir = os.path.abspath(self.save_dir)
        env = self.env
        print "Saving {FULL_IMAGE_NAME}".format(**env)
        filename = unicodedata.normalize('NFKD', env['FULL_IMAGE_NAME'].decode('UTF-8')).encode('ascii', 'ignore')
        filename = unicode(re.sub('[^\w\s-]', '', filename).strip().lower())
        filename = unicode(re.sub('[-\s]+', '-', filename) + '.tar.lz4')
        self.run_command('mkdir -p {}'.format(save_dir))
        env['SAVE_NAME'] = filename
        with cd(save_dir):
            cmd = 'docker save {DOCKER_IMAGE}:{VERSION} | lz4 -zc > {SAVE_NAME}'.format(**env)
            print cmd
            start = timer()
            print check_output(cmd, shell=True)
            end = timer()
            print "Elapsed Time: {:0.3f}s".format(end - start)

    def deploy_image(self):
        env = self.env
        if self.deploy:
            dry_run = False
        else:
            dry_run = True
        main_tag = '{DOCKER_IMAGE}:{VERSION}'.format(**env)
        extra_tags = ['{DOCKER_IMAGE}:{VERSION}-{DATE}'.format(**env)]
        for stag, version in self.special_tags.items():
            if version == env['VERSION']:
                extra_tags.append('{DOCKER_IMAGE}:{VERSION}-{STAG}'.format(STAG=stag, **env))

        for tag in extra_tags:
            self.run_command('docker tag {} {}'.format(main_tag, tag))
        self.run_command('docker push {}'.format(main_tag), dry_run=dry_run)

        if not dry_run:
            print "Logging in..."
            print check_output(shsplit('docker login -u {DOCKER_USER} -p {DOCKER_PASS}'.format(**os.environ)))
        for tag in extra_tags:
            self.run_command('docker push {}'.format(tag), dry_run=dry_run)

    def clean_temp(self):
        print "Deleting temp directory {}".format(self.tempdir)
        shutil.rmtree(self.tempdir)



if __name__ == '__main__':

    path=sys.argv[-1]
    print "Working Path {}".format(path)
    db = DockerBuild(path)
    pprint(db.__dict__)
    db.build_image()
    db.save_image()
    db.deploy_image()
    db.clean_temp()