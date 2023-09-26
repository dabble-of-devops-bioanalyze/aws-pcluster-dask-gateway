#!/usr/bin/env python

"""Tests for `aws_pcluster_dask_gateway` package."""

import unittest
from click.testing import CliRunner

from aws_pcluster_dask_gateway import aws_pcluster_dask_gateway
from aws_pcluster_dask_gateway import cli

import unittest

from aws_pcluster_helpers import (
    PClusterConfig,
    PClusterConfigFiles,
    InstanceTypesData,
    PClusterInstanceTypes,
    InstanceTypesMappings,
    size_in_gib,
)
from aws_pcluster_helpers.utils.logging import setup_logger
from aws_pcluster_helpers.models.config import (
    ENV_PCLUSTER_CONFIG_FILE,
    ENV_INSTANCE_TYPES_DATA_FILE,
    ENV_INSTANCE_TYPE_MAPPINGS_FILE,
)
import yaml
import json
import os
from devtools import PrettyFormat, pprint, pformat, debug
from rich.console import Console

from aws_pcluster_helpers.commands import cli_sinfo
from aws_pcluster_helpers.commands import cli_gen_nxf_slurm_config
from aws_pcluster_helpers.models.sinfo import SInfoTable, SinfoRow

instance_types_data_file = os.path.join(
    os.path.dirname(__file__), "instance-types-data.json"
)
instance_type_mapping_file = os.path.join(
    os.path.dirname(__file__), "instance_name_type_mappings.json"
)
pcluster_config_file = os.path.join(os.path.dirname(__file__), "pcluster_config.yml")

os.environ[ENV_INSTANCE_TYPE_MAPPINGS_FILE] = instance_type_mapping_file
os.environ[ENV_INSTANCE_TYPES_DATA_FILE] = instance_types_data_file
os.environ[ENV_PCLUSTER_CONFIG_FILE] = pcluster_config_file

logger = setup_logger(logger_name="tests", log_level="DEBUG")

from aws_pcluster_dask_gateway import DaskGatewaySlurmConfig


def test_files():
    assert os.path.exists(instance_type_mapping_file)
    assert os.path.exists(pcluster_config_file)
    assert os.path.exists(instance_types_data_file)


def test_dask_gateway():
    pcluster_config_files = PClusterConfigFiles(
        pcluster_config_file=pcluster_config_file,
        instance_types_data_file=instance_types_data_file,
        instance_type_mapping_file=instance_type_mapping_file,
    )
    dask_gateway_options = DaskGatewaySlurmConfig(pcluster_config_files=pcluster_config_files)
    assert dask_gateway_options
