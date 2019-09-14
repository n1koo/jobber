from os import path

import yaml
import os
import sys
import argparse
import logging
import coloredlogs

import time

from kubernetes.client.rest import ApiException
from kubernetes import client, config, watch

log = logging.getLogger("jobber")
LOGLEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=LOGLEVEL,
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)])
coloredlogs.install(isatty=True)


def parse_args():
    # parse command line arguments
    parser = argparse.ArgumentParser(description='Job runner')
    parser.add_argument(
        '--namespace', help='target namespace to run job in', default='default', type=str)
    parser.add_argument('--jobtemplate', help='location of the template',
                        default='migration-job.yaml', type=str)

    args = parser.parse_args()
    return args


def parse_template(file):
    with open(path.join(os.getcwd(), file)) as f:
        dep = yaml.safe_load(f)
    return dep


def clean_old_job(client, name, namespace):
    try:
        resp = client.read_namespaced_job_status(
            name=name, namespace=namespace)
        log.info("Old job still running, trying to clean out")
        log.debug("old one info: %s", resp.status)

        if not bool(resp.status.completion_time):
            log.error("Old job still running, bailing out")
            return False

        resp = client.delete_namespaced_job(
            name=name, namespace=namespace, grace_period_seconds=2)
        time.sleep(3)
        log.info("Old job pruned before running new one")
    except ApiException as ex:
        log.debug("ApiException %s", ex)
    return True


def wait_for_job_to_start(client, job, namespace):
    # Wait 20second for job to get active (/compleeted if fast enough to skip active check here)
    timeout = 20
    w = watch.Watch()
    log.info("Waiting for Job to get active")
    for event in w.stream(
            client.list_namespaced_job,
            label_selector="job-name=" + job,
            namespace=namespace,
            _request_timeout=timeout):
        if event['object'].status.active or event['object'].status.completion_time:
            w.stop()
            log.info("Job active")
            return event['object'].metadata.labels['controller-uid']
    # Hit timeout and job didn't get Active or completed
    log.error("Job did not get active withint %d seconds", timeout)
    return False


def get_pod_for_job(client, controller_uid, namespace):
    timeout = 20
    w = watch.Watch()
    log.info("Waiting for Pod")
    for event in w.stream(
            client.list_namespaced_pod,
            label_selector="controller-uid=" +
            controller_uid,
            namespace=namespace):
        if event['object'].status.phase == "Running" or event['object'].status.phase == "Succeeded":
            w.stop()
            log.info("Pod Running")
            return event['object'].metadata.name
        elif event['object'].status.phase == "Pending":
            log.debug("Waiting for Pod to start")
            continue
        elif event['object'].status.phase == "Failed":
            log.error("Pod %s failed to run, status %s",
                      event['object'].metadata.name, event['object'].status.phase)
            log.info(stream_logs(
                client, event['object'].metadata.name, namespace))
            return False
        else:
            log.error("Pod %s has unexpected state, status %s",
                      event['object'].metadata.name, event['object'].status.phase)
            return False
    # Hit timeout and job didn't get Active or completed
    log.error("Pod did not get active within %d seconds", timeout)
    return False


def stream_logs(client, pod_name, namespace):
    log.info(client.read_namespaced_pod_log(name=pod_name,
                                            namespace=namespace, follow=True, pretty=True))


def main():
    args = parse_args()
    config.load_kube_config()
    dep = parse_template(args.jobtemplate)
    k8s_batch_v1 = client.BatchV1Api()
    k8s_core_v1 = client.CoreV1Api()

    # Clean any lingering previous jobs
    success = clean_old_job(
        client=k8s_batch_v1, name=dep['metadata']['name'], namespace=args.namespace)
    if not success:
        os._exit(1)

    # Create new job from template
    resp = k8s_batch_v1.create_namespaced_job(
        body=dep, namespace=args.namespace)
    log.info("Job %s created", resp.metadata.name)

    # Check that pod started
    controller_uid = wait_for_job_to_start(
        client=k8s_batch_v1, job=resp.metadata.name, namespace=args.namespace)
    if not controller_uid:
        os._exit(1)

    # Grab pod name and block untils its running
    pod = get_pod_for_job(
        client=k8s_core_v1, controller_uid=controller_uid, namespace=args.namespace)
    if not pod:
        os._exit(1)

    # Stram pod logs
    stream_logs(client=k8s_core_v1, pod_name=pod, namespace=args.namespace)

    # Run finished, lets check what the end result was
    counter = 0
    while True:
        pod_status = k8s_core_v1.read_namespaced_pod_status(
            name=pod, namespace=args.namespace)
        if pod_status.status.phase == "Succeeded":
            log.info("Job finished, everything seemed go okay")
            os._exit(0)
        counter += 1
        log.info("Pod still in state %s, waiting, retry %d",
                 pod_status.status.phase, counter)
        if counter > 30:
            break
        time.sleep(1)

    log.error("Pod %s finished but without 0 exit code, status %s",
              pod, pod_status.status.phase)
    os._exit(1)


if __name__ == '__main__':
    main()
