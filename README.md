# Jobber

A helper to run k8s jobs as CI tasks and monitor their output and failures

## Running

Repo includes handly `local_run.sh` for locally testing

Otherwise `python3 run_migration.py`

### Arguments

- `--namespace`: name of the target namespace for job
- `--jobtemplate`: template name for the job, assumes its in same dir as this thing

## Notes

- Before run cleans up old dangling job *if* they are finished/failed
- Streams logs from the pod running job
- Assumes singleton pod, no retries
