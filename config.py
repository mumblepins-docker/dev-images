include_dirs = ['root-fs']

DOCKER_IMAGE = "mumblepins/circleci-dev"

fill_in_data = {
    'Dockerfile.meta': '### Build-time metadata ###'
}

save_dir = 'workspace'

special_tags = {
    'latest': 'stretch',
    'ubuntu': 'zesty',
    'ubuntu-LTS': 'xenial',
    'debian': 'stretch'
}
latest = 'stretch'

ignore_lines = [
    'Selecting previously unselected ',
    'Preparing to unpack',
    'update-alternatives'
]