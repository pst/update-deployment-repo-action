FROM python:3

ARG KUSTOMIZE_VERSION=4.0.5

RUN KUSTOMIZE_BINARY_PATH="https://github.com/kubernetes-sigs/kustomize/releases/download/kustomize/v${KUSTOMIZE_VERSION}/kustomize_v${KUSTOMIZE_VERSION}_linux_amd64.tar.gz"; \
    curl -LOs ${KUSTOMIZE_BINARY_PATH} && \
    tar -xf kustomize_v${KUSTOMIZE_VERSION}_linux_amd64.tar.gz && \
    rm kustomize_v${KUSTOMIZE_VERSION}_linux_amd64.tar.gz && \
    mv kustomize /usr/local/bin/kustomize && \
    chmod +x /usr/local/bin/kustomize && \
    kustomize version;

COPY Pipfile Pipfile.lock /opt/

WORKDIR /opt
RUN pip install --no-cache-dir pipenv &&\
    PIPENV_VENV_IN_PROJECT=true pipenv install

COPY action /opt/action

ENV PATH=/opt/.venv/bin:$PATH
ENTRYPOINT ["python", "/opt/action/main.py"]
