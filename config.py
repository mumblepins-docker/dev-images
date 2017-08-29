include_dirs = ['root-fs']

DOCKER_IMAGE = "mumblepins/circleci-dev"

fill_in_data = {
    'Dockerfile.meta': '### Build-time metadata ###'
}

save_dir = 'workspace'

latest='stretch'