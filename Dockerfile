FROM python:3-alpine3.9 as prod

WORKDIR /opt/app
ADD requirements.txt /opt/app/requirements.txt
RUN pip3 install -r /opt/app/requirements.txt

ADD run_job.py /opt/app/run_job.py
ADD run.sh /opt/app/run.sh

USER nobody

CMD ["/bin/sh", "-c", "/opt/app/run.sh"]

FROM prod as test

USER root

RUN pip3 install flake8
RUN pip3 install safety

USER nobody