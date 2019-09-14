#!/bin/bash

export PYTHONWARNINGS="ignore:Unverified HTTPS request"
#export LOG_LEVEL=DEBUG

python3 run_job.py "$@"
