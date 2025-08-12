FROM continuumio/miniconda3:latest AS miniconda

ARG CONDA_PROJECT_VERSION=0.4.2

SHELL ["/bin/bash", "-eo", "pipefail", "-c"]

LABEL maintainer="Conda Incubator"

LABEL io.k8s.description="Run Conda Project commands" \
      io.k8s.display-name="Conda Project ${CONDA_PROJECT_VERSION}" \
      io.openshift.expose-services="8086:http" \
      io.openshift.tags="builder,conda-project,conda" \
      io.openshift.s2i.scripts-url=image:///usr/libexec/s2i

ENV PATH=/opt/conda/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV HOME=/opt/project
ENV PIP_NO_CACHE_DIR=1

RUN conda install -n base -c defaults -c conda-forge conda-project=${CONDA_PROJECT_VERSION} tini -y \
    && conda clean --all --yes

COPY ./entrypoints/ /
COPY ./s2i/bin/ /usr/libexec/s2i

RUN mkdir -p /opt/project && \
    chown -R 1001:1001 /opt/project

USER 1001

WORKDIR $HOME

ENTRYPOINT ["/entrypoint.sh"]

CMD ["/usr/libexec/s2i/usage"]
