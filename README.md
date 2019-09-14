# Jobber

A helper to run k8s jobs as CI tasks and monitor their output and failures

![Screenshot 2019-09-14 at 11 06 23](https://user-images.githubusercontent.com/1556937/64905364-e6d0b780-d6df-11e9-827d-95113b0ad1cd.png)


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

