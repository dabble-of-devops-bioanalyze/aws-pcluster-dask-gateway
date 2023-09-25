from __future__ import annotations

import shutil
from aws_pcluster_helpers.models.sinfo import (SInfoTable, SinfoRow)
import functools
import os

from jinja2 import Environment, BaseLoader
import dataclasses
from typing import List, Any, TypedDict, Dict, Optional
from typing import ForwardRef
from devtools import PrettyFormat, pprint, pformat, debug
import json
import yaml
from datasize import DataSize

from aws_pcluster_helpers import (
    PClusterConfig,
    InstanceTypesData,
    PClusterInstanceTypes,
    InstanceTypesMappings,
    size_in_gib,
)

from aws_pcluster_helpers.models.instance_types_data import (
    PClusterInstanceTypes,
    InstanceTypesMappings,
)

from aws_pcluster_helpers.models import sinfo
from aws_pcluster_helpers import (
    PClusterConfig,
    InstanceTypesData,
    PClusterInstanceTypes,
    InstanceTypesMappings,
    size_in_gib,
)
from aws_pcluster_helpers.utils.logging import setup_logger
from aws_pcluster_helpers.models.config import PClusterConfigFiles

from traitlets import Unicode, default
from traitlets import Bool, Float, Integer, List, Unicode, default, validate

from dask_gateway_server.backends.jobqueue.slurm import SlurmClusterConfig, SlurmBackend, slurm_format_memory
from dask_gateway_server.options import Options, Select
from dask_gateway_server.options import Options, Select, String
from dask_gateway_server.traitlets import Command, Type
from pydantic import BaseModel, computed_field

logger = setup_logger('dask-gateway')

"""
Docs

https://gateway.dask.org/cluster-options.html
https://gateway.dask.org/install-jobqueue.html

"""


class DaskGatewaySlurmConfig(sinfo.SInfoTable):
    """
    Configure the Dask Gateway Cluster
    Each partition/instance type gets its own profile
    Users select from a dropdown menu

    https://gateway.dask.org/api-server.html?highlight=scheduler_mem#dask_gateway_server.backends.base.ClusterConfig.scheduler_memory

    Example
    -------
    Here we expose options for users to configure
    :data:`c.Backend.worker_cores` and
    :data:`c.Backend.worker_memory`. We set bounds on each resource to
    prevent users from requesting too large of a worker. The handler is used to
    convert the user specified memory from GiB to bytes (as expected by
    :data:`c.Backend.worker_memory`).
    .. code-block:: python
      from dask_gateway_server.options import Options, Integer, Float
      def options_handler(options):
          return {
              "worker_cores": options.worker_cores,
              "worker_memory": int(options.worker_memory * 2 ** 30)
          }
    """

    @computed_field
    @property
    def profiles(self) -> Dict[str, Dict[str, Any]]:
        profiles = {}
        for sinfo_row in self.rows:
            label = f"P: {sinfo_row.queue}, I: {sinfo_row.ec2_instance_type}, CPU: {sinfo_row.vcpu}, Mem: {sinfo_row.mem}"
            memory = sinfo_row.mem / sinfo_row.vcpu
            # Using all of the available memory is very error prone
            # instead use 95%
            memory = int(DataSize(f"{sinfo_row.mem - 1}Gi"))
            profiles[label] = {
                "worker_cores": sinfo_row.vcpu,
                "scheduler_cores": sinfo_row.vcpu,
                "worker_memory": memory,
                "scheduler_memory": memory,
                "constraint": sinfo_row.constraint,
                "partition": sinfo_row.queue,
                "wall_time": "08:00:00",
            }
        return profiles

    def __post_init__(self):
        return


class PClusterConfig(SlurmClusterConfig):
    """Dask cluster configuration options when running on SLURM"""
    partition = Unicode("", help="The partition to submit jobs to.", config=True)
    qos = Unicode("", help="QOS string associated with each job.", config=True)
    account = Unicode("", help="Account string associated with each job.", config=True)
    constraint = Unicode("", help="The job instance type constraint.", config=True)
    wall_time = Unicode("", help="The walltime. The cluster will be brought down after the wall time is complete.",
                        config=True)
    scheduler_cmd = Command(
        shutil.which("dask-scheduler"), help="Shell command to start a dask scheduler.", config=True
    )
    worker_cmd = Command(
        shutil.which("dask-worker"), help="Shell command to start a dask worker.", config=True
    )


def get_cluster_options(default_profile=None):
    """

    In your dask_gateway_config.py set the cluster options to cluster_options
    >>> c.Backend.cluster_options = cluster_options()


    :param default_profile:
    :return:
    """
    dask_gateway_slurm_config = DaskGatewaySlurmConfig()
    profile_names = list(dask_gateway_slurm_config.profiles.keys())
    if not default_profile:
        default_profile = profile_names[0]
    elif default_profile and default_profile not in profile_names:
        default_profile = profile_names[0]
    return Options(
        Select(
            "profile",
            profile_names,
            default=default_profile,
            label="Cluster Profile",
        ),
        String(
            "environment",
            label="Conda Environment"
        ),
        handler=lambda options: dask_gateway_slurm_config.profiles[options.profile],
    )


class PClusterBackend(SlurmBackend):
    cluster_options = get_cluster_options()
    dask_gateway_jobqueue_launcher = Unicode(
        shutil.which('dask-gateway-jobqueue-launcher'),
        help="The path to the dask-gateway-jobqueue-launcher executable", config=True
    )
    cluster_start_timeout = Float(
        3600,
        help="""
          Timeout (in seconds) before giving up on a starting dask cluster. Slurm requires a much longer startup time!
          """,
        config=True,
    )

    worker_start_timeout = Float(
        3600,
        help="""
          Timeout (in seconds) before giving up on a starting dask worker. Slurm requires a much longer startup time!
          """,
        config=True,
    )

    worker_start_failure_limit = Integer(
        10,
        help="""
        A limit on the number of failed attempts to start a worker before the
        cluster is marked as failed.
        Every worker that fails to start (timeouts exempt) increments a
        counter. The counter is reset if a worker successfully starts. If the
        counter ever exceeds this limit, the cluster is marked as failed and is
        shutdown.
        """,
        config=True,
    )

    backoff_base_delay = Float(
        0.5,
        help="""
        Base delay (in seconds) for backoff when retrying after failures.
        If an operation fails, it is retried after a backoff computed as:
        ```
        min(backoff_max_delay, backoff_base_delay * 2 ** num_failures)
        ```
        """,
        config=True,
    )

    cluster_config_class = Type(
        "aws_pcluster_dask_gateway.aws_pcluster_dask_gateway.PClusterConfig",
        klass="dask_gateway_server.backends.base.ClusterConfig",
        help="The cluster config class to use",
        config=True,
    )

    def get_submit_cmd_env_stdin(self, cluster, worker=None):
        cmd = []
        if worker:
            cmd = [self.submit_command, "--parsable", "--job-name=dask-gateway"]
        else:
            cmd = [self.submit_command, "--parsable", "--job-name=dask-gateway"]
        if cluster.config.partition:
            cmd.append("--partition=" + str(cluster.config.partition))
        if cluster.config.account:
            cmd.append("--account=" + str(cluster.config.account))
        if cluster.config.qos:
            cmd.append("--qos=" + str(cluster.config.qos))
        if cluster.config.constraint:
            cmd.append("--constraint=" + str(cluster.config.constraint))

        if worker:
            logger.info('Configuring dask-gateway worker')
            cpus = cluster.config.worker_cores
            mem = slurm_format_memory(cluster.config.worker_memory)
            log_file = "dask-worker-%s.log" % worker.name
            script = "\n".join(
                [
                    "#!/bin/sh",
                    cluster.config.worker_setup,
                    " ".join(self.get_worker_command(cluster, worker.name)),
                ]
            )
            env = self.get_worker_env(cluster)
        else:
            logger.info('Configuring dask-gateway scheduler')
            cpus = cluster.config.scheduler_cores
            mem = slurm_format_memory(cluster.config.worker_memory)
            log_file = "dask-scheduler-%s.log" % cluster.name
            script = "\n".join(
                [
                    "#!/bin/sh",
                    cluster.config.scheduler_setup,
                    " ".join(self.get_scheduler_command(cluster)),
                ]
            )
            env = self.get_scheduler_env(cluster)

        staging_dir = self.get_staging_directory(cluster)

        cmd.extend(
            [
                "--chdir=" + staging_dir,
                "--output=" + os.path.join(staging_dir, log_file),
                "--cpus-per-task=%d" % cpus,
                # "--mem=%s" % mem,
                "--export=%s" % (",".join(sorted(env))),
                "--exclusive",
            ]
        )

        logger.info(f'Cmd: {cmd}')
        logger.info(f'Env: {env}')
        logger.info(f'Script: {script}')
        return cmd, env, script
