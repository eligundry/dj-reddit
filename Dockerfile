FROM python:3.6-onbuild

RUN apt-get update \
    && apt-get -y upgrade \
    && rm -rf /var/lib/apt/lists/*

ENTRYPOINT ["python3", "dj.py", "run_server"]
