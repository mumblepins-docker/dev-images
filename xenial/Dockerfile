FROM buildpack-deps:xenial

RUN set -ex \
    && apt-get update \
    && apt-get -qq -o=Dpkg::Use-Pty=0 install --no-install-recommends \
        apt-transport-https \
        software-properties-common \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add - \
    && add-apt-repository \
        "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) \
        stable" \
    && apt-get update \
    && apt-get -qq -o=Dpkg::Use-Pty=0 install --no-install-recommends \
        docker-ce \
        python-pip \
        python-setuptools \
        liblz4-tool \
        build-essential \
        python-wheel \
        jq \
        nano \
    && apt-get -qq -o=Dpkg::Use-Pty=0 upgrade -y \
    && pip install semver \
    && rm -rf /var/lib/apt/lists/*

COPY root-fs /

RUN chmod +x /usr/local/bin/*

### Build-time metadata ###
### ###

CMD [ "/bin/bash" ]
