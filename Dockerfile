FROM python:3.9-slim
WORKDIR /opt
COPY . /opt
RUN apt-get update && apt-get -y install curl python3 python3-distutils
RUN python3 -m ensurepip && python3 -m pip install poetry
RUN poetry build

FROM alpine:edge
RUN apk add python3 ffmpeg gcc g++ make libffi-dev openssl-dev --no-cache
COPY --from=0 /opt/dist /opt/dist
RUN python3 -m ensurepip && python3 -m pip install /opt/dist/*.whl
VOLUME /db
EXPOSE 53211
CMD [ "hydownloader-daemon", "start", "--path", "/db" ]
