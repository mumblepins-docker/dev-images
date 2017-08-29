#!/usr/bin/env python
import os
import re

from build import splitall
from config import DockerConfig

paths = []
for root, dirs, files in os.walk(".", topdown=False):
    root = re.sub(r'^\./', '', root)
    fullpath = splitall(root)
    if fullpath[0].startswith('.'):
        continue
    if fullpath[0] in DockerConfig.include_dirs:
        continue
    if 'Dockerfile' not in files:
        continue

    paths.append(root)

with open('dockerlist', 'w') as fh:
    for path in paths:
        fh.write(path + '\n')
