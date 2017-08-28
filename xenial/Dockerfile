FROM buildpack-deps:xenial

RUN set -ex \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        apt-transport-https \
        software-properties-common \
    && curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add - \
    && add-apt-repository \
        "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
        $(lsb_release -cs) \
        stable" \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        docker-ce \
        python-pip \
        python-setuptools \
        liblz4-tool \
        build-essential \
        python-wheel \
        jq \
        nano \
    && apt-get upgrade -y \
    && pip install semver \
    && rm -rf /var/lib/apt/lists/*

COPY root-fs /

RUN chmod +x /usr/local/bin/*

# Build-time metadata as defined at http://label-schema.org
ARG BUILD_DATE
ARG VCS_REF
ARG VCS_URL
ARG VERSION
LABEL org.label-schema.build-date=$BUILD_DATE \
      org.label-schema.name="Docker-For-CircleCI" \
      org.label-schema.description="Docker for CircleCI" \
      org.label-schema.url="https://hub.docker.com/r/mumblepins/docker-on-debian-circleci/" \
      org.label-schema.vcs-ref=$VCS_REF \
      org.label-schema.vcs-url=$VCS_URL \
      org.label-schema.version=$VERSION \
      org.label-schema.schema-version="1.0" \
      maintainer="Daniel Sullivan <https://github.com/mumblepins>"

CMD [ "/bin/bash" ]
