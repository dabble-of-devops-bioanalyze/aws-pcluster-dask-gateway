=========================
aws_pcluster_dask_gateway
=========================

.. image:: https://img.shields.io/pypi/v/aws_pcluster_dask_gateway.svg
        :target: https://pypi.python.org/pypi/aws_pcluster_dask_gateway


A helper function to configure Dask Gateway to play nice with AWS PCluster


* Free software: Apache Software License 2.0
* Documentation: https://aws-pcluster-dask-gateway.readthedocs.io.


Features
--------

* Automatically parses parallelcluster's config files to generate a dask-gateway template. 
* Uses the jupyterhub-kubernetes profiles to list CPU/GPU

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
