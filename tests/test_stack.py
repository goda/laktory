from pathlib import Path

import pytest

from laktory import models
from laktory._settings import settings
from laktory._testing import skip_pulumi_preview
from laktory._testing import skip_terraform_plan

root = Path(__file__).parent


@pytest.fixture
def stack():
    with open(root / "data/stack.yaml", "r") as fp:
        stack = models.Stack.model_validate_yaml(fp)

    stack.terraform.backend = {
        "azurerm": {
            "resource_group_name": "o3-rg-laktory-dev",
            "storage_account_name": "o3stglaktorydev",
            "container_name": "unit-testing",
            "key": "terraform/dev.terraform.tfstate",
        }
    }

    return stack


@pytest.fixture
def full_stack():
    from tests.resources.test_alert import alert
    from tests.resources.test_catalog import catalog
    from tests.resources.test_cluster_policy import cluster_policy
    from tests.resources.test_dashboard import dashboard
    from tests.resources.test_directory import directory
    from tests.resources.test_job import job
    from tests.resources.test_job import job_for_each
    from tests.resources.test_metastore import metastore
    from tests.resources.test_mlflow_experiment import mlexp
    from tests.resources.test_mlflow_model import mlmodel
    from tests.resources.test_mlflow_webhook import mlwebhook
    from tests.resources.test_notebook import get_notebook
    from tests.resources.test_permissions import permissions
    from tests.resources.test_pipeline_orchestrators import get_pl_dlt
    from tests.resources.test_query import query
    from tests.resources.test_repo import repo
    from tests.resources.test_schema import schema
    from tests.resources.test_user import group
    from tests.resources.test_user import user
    from tests.resources.test_vectorsearchendpoint import vector_search_endpoint
    from tests.resources.test_vectorsearchindex import vector_search_index
    from tests.resources.test_workspacebinding import workspace_binding
    from tests.resources.test_workspacefile import get_workspace_file

    # Update paths because preview is executed in tmp_path
    nb = get_notebook()
    workspace_file = get_workspace_file()
    nb.source = str(root / "resources" / nb.source)
    workspace_file.source = str(root / "resources" / workspace_file.source)

    _resources = {
        "databricks_alerts": [alert],
        "databricks_catalogs": [catalog],
        "databricks_clusterpolicies": [cluster_policy],
        "databricks_dashboards": [dashboard],
        "databricks_directories": [directory],
        "databricks_jobs": [job, job_for_each],
        "databricks_metastores": [metastore],
        "databricks_mlflowexperiments": [mlexp],
        "databricks_mlflowmodels": [mlmodel],
        "databricks_mlflowwebhooks": [mlwebhook],
        "databricks_notebooks": [nb],
        "databricks_permissions": [permissions],
        "databricks_queries": [query],
        "databricks_repos": [repo],
        "databricks_schemas": [schema],
        "databricks_groups": [group],
        "databricks_users": [user],
        "databricks_vectorsearchendpoints": [vector_search_endpoint],
        "databricks_vectorsearchindexes": [vector_search_index],
        "databricks_workspacefiles": [workspace_file],
        "databricks_workspacebindings": [workspace_binding],
        "pipelines": [get_pl_dlt()],  # required by job
    }

    resources = {}
    for k, v in _resources.items():
        resources[k] = {r.resource_name: r for r in v}

    resources["providers"] = {
        "provider-workspace-neptune": {
            "host": "${vars.DATABRICKS_HOST}",
            # "azure_client_id": "0",
            # "azure_client_secret": "0",
            # "azure_tenant_id": "0",
        },
        "databricks": {
            "host": "${vars.DATABRICKS_HOST}",
            "token": "${vars.DATABRICKS_TOKEN}",
        },
        "databricks1": {
            "host": "${vars.DATABRICKS_HOST}",
        },
        "databricks2": {
            "host": "${vars.DATABRICKS_HOST}",
        },
    }

    stack = models.Stack(
        organization="okube",
        name="unit-testing",
        backend="pulumi",
        pulumi={
            "config": {
                "databricks:host": "${vars.DATABRICKS_HOST}",
                "databricks:token": "${vars.DATABRICKS_TOKEN}",
            }
        },
        resources=resources,
        environments={"dev": {}},
    )

    return stack


def test_stack_model(stack):
    stack.model_dump()


def test_stack_env_model(stack):
    # dev
    _stack = stack.get_env("dev").inject_vars()
    pl = _stack.resources.pipelines["pl-custom-name"]

    assert _stack.variables == {
        "business_unit": "laktory",
        "workflow_name": "UNDEFINED",
        "env": "dev",
        "is_dev": True,
        "node_type_id": "Standard_DS3_v2",
    }
    assert pl.orchestrator.development is None
    assert pl.nodes[0].dlt_template is None
    assert (
        pl.orchestrator.config_file.path
        == "/.laktory/pipelines/pl-stock-prices-ut-stack/config.json"
    )
    assert pl.variables == {
        "workflow_name": "pl-stock-prices-ut-stack",
        "business_unit": "laktory",
        "env": "dev",
        "is_dev": True,
        "node_type_id": "Standard_DS3_v2",
    }

    # prod
    _stack = stack.get_env("prod")
    pl = _stack.resources.pipelines["pl-custom-name"]
    assert _stack.variables == {
        "business_unit": "laktory",
        "workflow_name": "UNDEFINED",
        "env": "prod",
        "is_dev": False,
        "node_type_id": "Standard_DS4_v2",
    }
    assert not pl.orchestrator.development
    assert pl.nodes[0].dlt_template is None
    assert pl.variables == {
        "workflow_name": "pl-stock-prices-ut-stack",
        "business_unit": "laktory",
        "env": "prod",
        "is_dev": False,
        "node_type_id": "Standard_DS4_v2",
    }


def test_stack_resources_unique_name():
    with pytest.raises(ValueError):
        models.Stack(
            name="stack",
            organization="o3",
            resources=models.StackResources(
                databricks_schemas={"finance": {"name": "schema_finance"}},
                databricks_catalogs={
                    "finance": {
                        "name": "catalog_finance",
                    }
                },
            ),
        )


def test_pulumi_stack(monkeypatch, stack):
    monkeypatch.setenv("DATABRICKS_HOST", "my-host")
    monkeypatch.setenv("DATABRICKS_TOKEN", "my-token")

    pstack = stack.to_pulumi(env_name=None)
    assert pstack.organization == "okube"

    data_default = pstack.model_dump()

    assert data_default == {
        "variables": {},
        "name": "unit-testing",
        "runtime": "yaml",
        "config": {"databricks:host": "my-host", "databricks:token": "my-token"},
        "resources": {
            "job-stock-prices-ut-stack": {
                "type": "databricks:Job",
                "properties": {
                    "name": "job-stock-prices-ut-stack",
                    "parameters": [],
                    "tags": {},
                    "tasks": [
                        {
                            "libraries": [
                                {"pypi": {"package": "laktory==0.0.27"}},
                                {"pypi": {"package": "yfinance"}},
                            ],
                            "jobClusterKey": "main",
                            "notebookTask": {
                                "notebookPath": "/jobs/ingest_stock_metadata.py"
                            },
                            "taskKey": "ingest-metadata",
                        },
                        {
                            "pipelineTask": {"pipelineId": "${dlt-custom-name.id}"},
                            "taskKey": "run-pipeline",
                        },
                    ],
                    "jobClusters": [
                        {
                            "jobClusterKey": "main",
                            "newCluster": {
                                "dataSecurityMode": "USER_ISOLATION",
                                "initScripts": [],
                                "nodeTypeId": "${vars.node_type_id}",
                                "sparkConf": {},
                                "sparkEnvVars": {
                                    "AZURE_TENANT_ID": "{{secrets/azure/tenant-id}}",
                                    "LAKTORY_WORKSPACE_ENV": "${vars.env}",
                                },
                                "sparkVersion": "16.3.x-scala2.12",
                                "sshPublicKeys": [],
                            },
                        }
                    ],
                },
                "options": {},
            },
            "notebook-external": {
                "type": "databricks:Notebook",
                "options": {},
                "get": {"id": "/Workspace/external"},
            },
            "permissions-notebook-external": {
                "type": "databricks:Permissions",
                "properties": {
                    "accessControls": [
                        {"groupName": "role-analysts", "permissionLevel": "CAN_READ"}
                    ],
                    "notebookPath": "${notebook-external.path}",
                },
                "options": {"dependsOn": ["${notebook-external}"]},
            },
            "warehouse-external": {
                "type": "databricks:SqlEndpoint",
                "options": {},
                "get": {"id": "d2fa41bf94858c4b"},
            },
            "permissions-warehouse-external": {
                "type": "databricks:Permissions",
                "properties": {
                    "accessControls": [
                        {"groupName": "role-analysts", "permissionLevel": "CAN_USE"}
                    ],
                    "sqlEndpointId": "${warehouse-external.id}",
                },
                "options": {"dependsOn": ["${warehouse-external}"]},
            },
            "permissions_test": {
                "options": {},
                "properties": {
                    "accessControls": [
                        {
                            "permissionLevel": "CAN_MANAGE",
                            "userName": "user1",
                        },
                        {
                            "permissionLevel": "CAN_RUN",
                            "userName": "user2",
                        },
                    ],
                    "pipelineId": "pipeline_123",
                },
                "type": "databricks:Permissions",
            },
            "dlt-custom-name": {
                "type": "databricks:Pipeline",
                "properties": {
                    "channel": "PREVIEW",
                    "clusters": [],
                    "configuration": {
                        "business_unit": "laktory",
                        "workflow_name": "pl-stock-prices-ut-stack",
                        "pipeline_name": "pl-stock-prices-ut-stack",
                        "workspace_laktory_root": "/.laktory/",
                    },
                    "libraries": [
                        {"notebook": {"path": "/pipelines/dlt_brz_template.py"}}
                    ],
                    "name": "pl-stock-prices-ut-stack",
                    "notifications": [],
                },
                "options": {"provider": "${databricks}", "dependsOn": []},
            },
            "permissions-dlt-custom-name": {
                "type": "databricks:Permissions",
                "properties": {
                    "accessControls": [
                        {"groupName": "account users", "permissionLevel": "CAN_VIEW"},
                        {"groupName": "role-engineers", "permissionLevel": "CAN_RUN"},
                    ],
                    "pipelineId": "${dlt-custom-name.id}",
                },
                "options": {
                    "provider": "${databricks}",
                    "dependsOn": ["${dlt-custom-name}"],
                },
            },
            "workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-config-json": {
                "type": "databricks:WorkspaceFile",
                "properties": {
                    "path": "/.laktory/pipelines/pl-stock-prices-ut-stack/config.json",
                    "source": "./tmp-pl-stock-prices-ut-stack-config.json",
                },
                "options": {
                    "provider": "${databricks}",
                    "dependsOn": ["${dlt-custom-name}"],
                },
            },
            "permissions-workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-config-json": {
                "type": "databricks:Permissions",
                "properties": {
                    "accessControls": [
                        {"groupName": "users", "permissionLevel": "CAN_READ"}
                    ],
                    "workspaceFilePath": "/.laktory/pipelines/pl-stock-prices-ut-stack/config.json",
                },
                "options": {
                    "provider": "${databricks}",
                    "dependsOn": [
                        "${workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-config-json}"
                    ],
                },
            },
            "workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-requirements-txt": {
                "type": "databricks:WorkspaceFile",
                "properties": {
                    "path": "/.laktory/pipelines/pl-stock-prices-ut-stack/requirements.txt",
                    "source": "./tmp-pl-stock-prices-ut-stack-requirements.txt",
                },
                "options": {
                    "provider": "${databricks}",
                    "dependsOn": ["${dlt-custom-name}"],
                },
            },
            "permissions-workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-requirements-txt": {
                "type": "databricks:Permissions",
                "properties": {
                    "accessControls": [
                        {"groupName": "users", "permissionLevel": "CAN_READ"}
                    ],
                    "workspaceFilePath": "/.laktory/pipelines/pl-stock-prices-ut-stack/requirements.txt",
                },
                "options": {
                    "provider": "${databricks}",
                    "dependsOn": [
                        "${workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-requirements-txt}"
                    ],
                },
            },
            "databricks": {
                "type": "pulumi:providers:databricks",
                "properties": {"host": "my-host", "token": "my-token"},
                "options": {},
            },
        },
        "outputs": {},
    }

    # Prod
    data = stack.to_pulumi(env_name="prod").model_dump()
    assert data == {
        "variables": {},
        "name": "unit-testing",
        "runtime": "yaml",
        "config": {"databricks:host": "my-host", "databricks:token": "my-token"},
        "resources": {
            "job-stock-prices-ut-stack": {
                "type": "databricks:Job",
                "properties": {
                    "name": "job-stock-prices-ut-stack",
                    "parameters": [],
                    "tags": {},
                    "tasks": [
                        {
                            "libraries": [
                                {"pypi": {"package": "laktory==0.0.27"}},
                                {"pypi": {"package": "yfinance"}},
                            ],
                            "jobClusterKey": "main",
                            "notebookTask": {
                                "notebookPath": "/jobs/ingest_stock_metadata.py"
                            },
                            "taskKey": "ingest-metadata",
                        },
                        {
                            "pipelineTask": {"pipelineId": "${dlt-custom-name.id}"},
                            "taskKey": "run-pipeline",
                        },
                    ],
                    "jobClusters": [
                        {
                            "jobClusterKey": "main",
                            "newCluster": {
                                "dataSecurityMode": "USER_ISOLATION",
                                "initScripts": [],
                                "nodeTypeId": "Standard_DS4_v2",
                                "sparkConf": {},
                                "sparkEnvVars": {
                                    "AZURE_TENANT_ID": "{{secrets/azure/tenant-id}}",
                                    "LAKTORY_WORKSPACE_ENV": "prod",
                                },
                                "sparkVersion": "16.3.x-scala2.12",
                                "sshPublicKeys": [],
                            },
                        }
                    ],
                },
                "options": {},
            },
            "notebook-external": {
                "type": "databricks:Notebook",
                "options": {},
                "get": {"id": "/Workspace/external"},
            },
            "permissions-notebook-external": {
                "type": "databricks:Permissions",
                "properties": {
                    "accessControls": [
                        {"groupName": "role-analysts", "permissionLevel": "CAN_READ"}
                    ],
                    "notebookPath": "${notebook-external.path}",
                },
                "options": {"dependsOn": ["${notebook-external}"]},
            },
            "warehouse-external": {
                "type": "databricks:SqlEndpoint",
                "options": {},
                "get": {"id": "d2fa41bf94858c4b"},
            },
            "permissions-warehouse-external": {
                "type": "databricks:Permissions",
                "properties": {
                    "accessControls": [
                        {"groupName": "role-analysts", "permissionLevel": "CAN_USE"}
                    ],
                    "sqlEndpointId": "${warehouse-external.id}",
                },
                "options": {"dependsOn": ["${warehouse-external}"]},
            },
            "dlt-custom-name": {
                "type": "databricks:Pipeline",
                "properties": {
                    "channel": "PREVIEW",
                    "clusters": [],
                    "configuration": {
                        "business_unit": "laktory",
                        "workflow_name": "pl-stock-prices-ut-stack",
                        "pipeline_name": "pl-stock-prices-ut-stack",
                        "workspace_laktory_root": "/.laktory/",
                    },
                    "development": False,
                    "libraries": [
                        {"notebook": {"path": "/pipelines/dlt_brz_template.py"}}
                    ],
                    "name": "pl-stock-prices-ut-stack",
                    "notifications": [],
                },
                "options": {"provider": "${databricks}", "dependsOn": []},
            },
            "permissions-dlt-custom-name": {
                "type": "databricks:Permissions",
                "properties": {
                    "accessControls": [
                        {"groupName": "account users", "permissionLevel": "CAN_VIEW"},
                        {"groupName": "role-engineers", "permissionLevel": "CAN_RUN"},
                    ],
                    "pipelineId": "${dlt-custom-name.id}",
                },
                "options": {
                    "provider": "${databricks}",
                    "dependsOn": ["${dlt-custom-name}"],
                },
            },
            "workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-config-json": {
                "type": "databricks:WorkspaceFile",
                "properties": {
                    "path": "/.laktory/pipelines/pl-stock-prices-ut-stack/config.json",
                    "source": "./tmp-pl-stock-prices-ut-stack-config.json",
                },
                "options": {
                    "provider": "${databricks}",
                    "dependsOn": ["${dlt-custom-name}"],
                },
            },
            "permissions-workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-config-json": {
                "type": "databricks:Permissions",
                "properties": {
                    "accessControls": [
                        {"groupName": "users", "permissionLevel": "CAN_READ"}
                    ],
                    "workspaceFilePath": "/.laktory/pipelines/pl-stock-prices-ut-stack/config.json",
                },
                "options": {
                    "provider": "${databricks}",
                    "dependsOn": [
                        "${workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-config-json}"
                    ],
                },
            },
            "workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-requirements-txt": {
                "type": "databricks:WorkspaceFile",
                "properties": {
                    "path": "/.laktory/pipelines/pl-stock-prices-ut-stack/requirements.txt",
                    "source": "./tmp-pl-stock-prices-ut-stack-requirements.txt",
                },
                "options": {
                    "provider": "${databricks}",
                    "dependsOn": ["${dlt-custom-name}"],
                },
            },
            "permissions-workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-requirements-txt": {
                "type": "databricks:Permissions",
                "properties": {
                    "accessControls": [
                        {"groupName": "users", "permissionLevel": "CAN_READ"}
                    ],
                    "workspaceFilePath": "/.laktory/pipelines/pl-stock-prices-ut-stack/requirements.txt",
                },
                "options": {
                    "provider": "${databricks}",
                    "dependsOn": [
                        "${workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-requirements-txt}"
                    ],
                },
            },
            "permissions_test": {
                "options": {},
                "properties": {
                    "accessControls": [
                        {
                            "permissionLevel": "CAN_MANAGE",
                            "userName": "user1",
                        },
                        {
                            "permissionLevel": "CAN_RUN",
                            "userName": "user2",
                        },
                    ],
                    "pipelineId": "pipeline_123",
                },
                "type": "databricks:Permissions",
            },
            "databricks": {
                "type": "pulumi:providers:databricks",
                "properties": {"host": "my-host", "token": "my-token"},
                "options": {},
            },
        },
        "outputs": {},
    }


def test_terraform_stack(monkeypatch, stack):
    # To prevent from exposing sensitive data, we overwrite some env vars
    monkeypatch.setenv("DATABRICKS_HOST", "my-host")
    monkeypatch.setenv("DATABRICKS_TOKEN", "my-token")

    data_default = stack.to_terraform().model_dump()
    assert data_default == {
        "terraform": {
            "required_providers": {
                "databricks": {"source": "databricks/databricks", "version": ">=1.49"}
            },
            "backend": {
                "azurerm": {
                    "resource_group_name": "o3-rg-laktory-dev",
                    "storage_account_name": "o3stglaktorydev",
                    "container_name": "unit-testing",
                    "key": "terraform/dev.terraform.tfstate",
                }
            },
        },
        "provider": {"databricks": {"host": "my-host", "token": "my-token"}},
        "resource": {
            "databricks_job": {
                "job-stock-prices-ut-stack": {
                    "name": "job-stock-prices-ut-stack",
                    "tags": {},
                    "parameter": [],
                    "task": [
                        {
                            "job_cluster_key": "main",
                            "notebook_task": {
                                "notebook_path": "/jobs/ingest_stock_metadata.py"
                            },
                            "task_key": "ingest-metadata",
                            "library": [
                                {"pypi": {"package": "laktory==0.0.27"}},
                                {"pypi": {"package": "yfinance"}},
                            ],
                        },
                        {
                            "pipeline_task": {
                                "pipeline_id": "${databricks_pipeline.dlt-custom-name.id}"
                            },
                            "task_key": "run-pipeline",
                        },
                    ],
                    "job_cluster": [
                        {
                            "job_cluster_key": "main",
                            "new_cluster": {
                                "data_security_mode": "USER_ISOLATION",
                                "init_scripts": [],
                                "node_type_id": "${vars.node_type_id}",
                                "spark_conf": {},
                                "spark_env_vars": {
                                    "AZURE_TENANT_ID": "{{secrets/azure/tenant-id}}",
                                    "LAKTORY_WORKSPACE_ENV": "${vars.env}",
                                },
                                "spark_version": "16.3.x-scala2.12",
                                "ssh_public_keys": [],
                            },
                        }
                    ],
                }
            },
            "databricks_permissions": {
                "permissions-notebook-external": {
                    "notebook_path": "${data.databricks_notebook.notebook-external.path}",
                    "access_control": [
                        {"group_name": "role-analysts", "permission_level": "CAN_READ"}
                    ],
                    "depends_on": ["data.databricks_notebook.notebook-external"],
                },
                "permissions-warehouse-external": {
                    "sql_endpoint_id": "${data.databricks_sql_warehouse.warehouse-external.id}",
                    "access_control": [
                        {"group_name": "role-analysts", "permission_level": "CAN_USE"}
                    ],
                    "depends_on": ["data.databricks_sql_warehouse.warehouse-external"],
                },
                "permissions-dlt-custom-name": {
                    "pipeline_id": "${databricks_pipeline.dlt-custom-name.id}",
                    "access_control": [
                        {"group_name": "account users", "permission_level": "CAN_VIEW"},
                        {"group_name": "role-engineers", "permission_level": "CAN_RUN"},
                    ],
                    "depends_on": ["databricks_pipeline.dlt-custom-name"],
                    "provider": "databricks",
                },
                "permissions-workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-config-json": {
                    "workspace_file_path": "/.laktory/pipelines/pl-stock-prices-ut-stack/config.json",
                    "access_control": [
                        {"group_name": "users", "permission_level": "CAN_READ"}
                    ],
                    "depends_on": [
                        "databricks_workspace_file.workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-config-json"
                    ],
                    "provider": "databricks",
                },
                "permissions-workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-requirements-txt": {
                    "workspace_file_path": "/.laktory/pipelines/pl-stock-prices-ut-stack/requirements.txt",
                    "access_control": [
                        {"group_name": "users", "permission_level": "CAN_READ"}
                    ],
                    "depends_on": [
                        "databricks_workspace_file.workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-requirements-txt"
                    ],
                    "provider": "databricks",
                },
                "permissions_test": {
                    "access_control": [
                        {
                            "permission_level": "CAN_MANAGE",
                            "user_name": "user1",
                        },
                        {
                            "permission_level": "CAN_RUN",
                            "user_name": "user2",
                        },
                    ],
                    "pipeline_id": "pipeline_123",
                },
            },
            "databricks_pipeline": {
                "dlt-custom-name": {
                    "channel": "PREVIEW",
                    "configuration": {
                        "business_unit": "laktory",
                        "workflow_name": "pl-stock-prices-ut-stack",
                        "pipeline_name": "pl-stock-prices-ut-stack",
                        "workspace_laktory_root": "/.laktory/",
                    },
                    "name": "pl-stock-prices-ut-stack",
                    "cluster": [],
                    "library": [
                        {"notebook": {"path": "/pipelines/dlt_brz_template.py"}}
                    ],
                    "notification": [],
                    "provider": "databricks",
                }
            },
            "databricks_workspace_file": {
                "workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-config-json": {
                    "path": "/.laktory/pipelines/pl-stock-prices-ut-stack/config.json",
                    "source": "./tmp-pl-stock-prices-ut-stack-config.json",
                    "depends_on": ["databricks_pipeline.dlt-custom-name"],
                    "provider": "databricks",
                },
                "workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-requirements-txt": {
                    "path": "/.laktory/pipelines/pl-stock-prices-ut-stack/requirements.txt",
                    "source": "./tmp-pl-stock-prices-ut-stack-requirements.txt",
                    "depends_on": ["databricks_pipeline.dlt-custom-name"],
                    "provider": "databricks",
                },
            },
        },
        "data": {
            "databricks_notebook": {
                "notebook-external": {"path": "/Workspace/external", "format": "SOURCE"}
            },
            "databricks_sql_warehouse": {
                "warehouse-external": {"id": "d2fa41bf94858c4b", "name": None}
            },
        },
    }

    # Dev
    data = stack.to_terraform(env_name="dev").model_dump()
    assert data == {
        "terraform": {
            "required_providers": {
                "databricks": {"source": "databricks/databricks", "version": ">=1.49"}
            }
        },
        "provider": {"databricks": {"host": "my-host", "token": "my-token"}},
        "resource": {
            "databricks_job": {
                "job-stock-prices-ut-stack": {
                    "name": "job-stock-prices-ut-stack",
                    "tags": {},
                    "parameter": [],
                    "task": [
                        {
                            "job_cluster_key": "main",
                            "notebook_task": {
                                "notebook_path": "/jobs/ingest_stock_metadata.py"
                            },
                            "task_key": "ingest-metadata",
                            "library": [
                                {"pypi": {"package": "laktory==0.0.27"}},
                                {"pypi": {"package": "yfinance"}},
                            ],
                        },
                        {
                            "pipeline_task": {
                                "pipeline_id": "${databricks_pipeline.dlt-custom-name.id}"
                            },
                            "task_key": "run-pipeline",
                        },
                    ],
                    "job_cluster": [
                        {
                            "job_cluster_key": "main",
                            "new_cluster": {
                                "data_security_mode": "USER_ISOLATION",
                                "init_scripts": [],
                                "node_type_id": "Standard_DS3_v2",
                                "spark_conf": {},
                                "spark_env_vars": {
                                    "AZURE_TENANT_ID": "{{secrets/azure/tenant-id}}",
                                    "LAKTORY_WORKSPACE_ENV": "dev",
                                },
                                "spark_version": "16.3.x-scala2.12",
                                "ssh_public_keys": [],
                            },
                        }
                    ],
                }
            },
            "databricks_permissions": {
                "permissions-notebook-external": {
                    "notebook_path": "${data.databricks_notebook.notebook-external.path}",
                    "access_control": [
                        {"group_name": "role-analysts", "permission_level": "CAN_READ"}
                    ],
                    "depends_on": ["data.databricks_notebook.notebook-external"],
                },
                "permissions-warehouse-external": {
                    "sql_endpoint_id": "${data.databricks_sql_warehouse.warehouse-external.id}",
                    "access_control": [
                        {"group_name": "role-analysts", "permission_level": "CAN_USE"}
                    ],
                    "depends_on": ["data.databricks_sql_warehouse.warehouse-external"],
                },
                "permissions-dlt-custom-name": {
                    "pipeline_id": "${databricks_pipeline.dlt-custom-name.id}",
                    "access_control": [
                        {"group_name": "account users", "permission_level": "CAN_VIEW"},
                        {"group_name": "role-engineers", "permission_level": "CAN_RUN"},
                    ],
                    "depends_on": ["databricks_pipeline.dlt-custom-name"],
                    "provider": "databricks",
                },
                "permissions-workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-config-json": {
                    "workspace_file_path": "/.laktory/pipelines/pl-stock-prices-ut-stack/config.json",
                    "access_control": [
                        {"group_name": "users", "permission_level": "CAN_READ"}
                    ],
                    "depends_on": [
                        "databricks_workspace_file.workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-config-json"
                    ],
                    "provider": "databricks",
                },
                "permissions-workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-requirements-txt": {
                    "workspace_file_path": "/.laktory/pipelines/pl-stock-prices-ut-stack/requirements.txt",
                    "access_control": [
                        {"group_name": "users", "permission_level": "CAN_READ"}
                    ],
                    "depends_on": [
                        "databricks_workspace_file.workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-requirements-txt"
                    ],
                    "provider": "databricks",
                },
                "permissions_test": {
                    "access_control": [
                        {
                            "permission_level": "CAN_MANAGE",
                            "user_name": "user1",
                        },
                        {
                            "permission_level": "CAN_RUN",
                            "user_name": "user2",
                        },
                    ],
                    "pipeline_id": "pipeline_123",
                },
            },
            "databricks_pipeline": {
                "dlt-custom-name": {
                    "channel": "PREVIEW",
                    "configuration": {
                        "business_unit": "laktory",
                        "workflow_name": "pl-stock-prices-ut-stack",
                        "pipeline_name": "pl-stock-prices-ut-stack",
                        "workspace_laktory_root": "/.laktory/",
                    },
                    "name": "pl-stock-prices-ut-stack",
                    "cluster": [],
                    "library": [
                        {"notebook": {"path": "/pipelines/dlt_brz_template.py"}}
                    ],
                    "notification": [],
                    "provider": "databricks",
                }
            },
            "databricks_workspace_file": {
                "workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-config-json": {
                    "path": "/.laktory/pipelines/pl-stock-prices-ut-stack/config.json",
                    "source": "./tmp-pl-stock-prices-ut-stack-config.json",
                    "depends_on": ["databricks_pipeline.dlt-custom-name"],
                    "provider": "databricks",
                },
                "workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-requirements-txt": {
                    "path": "/.laktory/pipelines/pl-stock-prices-ut-stack/requirements.txt",
                    "source": "./tmp-pl-stock-prices-ut-stack-requirements.txt",
                    "depends_on": ["databricks_pipeline.dlt-custom-name"],
                    "provider": "databricks",
                },
            },
        },
        "data": {
            "databricks_notebook": {
                "notebook-external": {"path": "/Workspace/external", "format": "SOURCE"}
            },
            "databricks_sql_warehouse": {
                "warehouse-external": {"id": "d2fa41bf94858c4b", "name": None}
            },
        },
    }

    # Prod
    data = stack.to_terraform(env_name="prod").model_dump()
    assert data == {
        "terraform": {
            "required_providers": {
                "databricks": {"source": "databricks/databricks", "version": ">=1.49"}
            }
        },
        "provider": {"databricks": {"host": "my-host", "token": "my-token"}},
        "resource": {
            "databricks_job": {
                "job-stock-prices-ut-stack": {
                    "name": "job-stock-prices-ut-stack",
                    "tags": {},
                    "parameter": [],
                    "task": [
                        {
                            "job_cluster_key": "main",
                            "notebook_task": {
                                "notebook_path": "/jobs/ingest_stock_metadata.py"
                            },
                            "task_key": "ingest-metadata",
                            "library": [
                                {"pypi": {"package": "laktory==0.0.27"}},
                                {"pypi": {"package": "yfinance"}},
                            ],
                        },
                        {
                            "pipeline_task": {
                                "pipeline_id": "${databricks_pipeline.dlt-custom-name.id}"
                            },
                            "task_key": "run-pipeline",
                        },
                    ],
                    "job_cluster": [
                        {
                            "job_cluster_key": "main",
                            "new_cluster": {
                                "data_security_mode": "USER_ISOLATION",
                                "init_scripts": [],
                                "node_type_id": "Standard_DS4_v2",
                                "spark_conf": {},
                                "spark_env_vars": {
                                    "AZURE_TENANT_ID": "{{secrets/azure/tenant-id}}",
                                    "LAKTORY_WORKSPACE_ENV": "prod",
                                },
                                "spark_version": "16.3.x-scala2.12",
                                "ssh_public_keys": [],
                            },
                        }
                    ],
                }
            },
            "databricks_permissions": {
                "permissions-notebook-external": {
                    "notebook_path": "${data.databricks_notebook.notebook-external.path}",
                    "access_control": [
                        {"group_name": "role-analysts", "permission_level": "CAN_READ"}
                    ],
                    "depends_on": ["data.databricks_notebook.notebook-external"],
                },
                "permissions-warehouse-external": {
                    "sql_endpoint_id": "${data.databricks_sql_warehouse.warehouse-external.id}",
                    "access_control": [
                        {"group_name": "role-analysts", "permission_level": "CAN_USE"}
                    ],
                    "depends_on": ["data.databricks_sql_warehouse.warehouse-external"],
                },
                "permissions-dlt-custom-name": {
                    "pipeline_id": "${databricks_pipeline.dlt-custom-name.id}",
                    "access_control": [
                        {"group_name": "account users", "permission_level": "CAN_VIEW"},
                        {"group_name": "role-engineers", "permission_level": "CAN_RUN"},
                    ],
                    "depends_on": ["databricks_pipeline.dlt-custom-name"],
                    "provider": "databricks",
                },
                "permissions-workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-config-json": {
                    "workspace_file_path": "/.laktory/pipelines/pl-stock-prices-ut-stack/config.json",
                    "access_control": [
                        {"group_name": "users", "permission_level": "CAN_READ"}
                    ],
                    "depends_on": [
                        "databricks_workspace_file.workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-config-json"
                    ],
                    "provider": "databricks",
                },
                "permissions-workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-requirements-txt": {
                    "workspace_file_path": "/.laktory/pipelines/pl-stock-prices-ut-stack/requirements.txt",
                    "access_control": [
                        {"group_name": "users", "permission_level": "CAN_READ"}
                    ],
                    "depends_on": [
                        "databricks_workspace_file.workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-requirements-txt"
                    ],
                    "provider": "databricks",
                },
                "permissions_test": {
                    "access_control": [
                        {
                            "permission_level": "CAN_MANAGE",
                            "user_name": "user1",
                        },
                        {
                            "permission_level": "CAN_RUN",
                            "user_name": "user2",
                        },
                    ],
                    "pipeline_id": "pipeline_123",
                },
            },
            "databricks_pipeline": {
                "dlt-custom-name": {
                    "channel": "PREVIEW",
                    "configuration": {
                        "business_unit": "laktory",
                        "workflow_name": "pl-stock-prices-ut-stack",
                        "pipeline_name": "pl-stock-prices-ut-stack",
                        "workspace_laktory_root": "/.laktory/",
                    },
                    "development": False,
                    "name": "pl-stock-prices-ut-stack",
                    "cluster": [],
                    "library": [
                        {"notebook": {"path": "/pipelines/dlt_brz_template.py"}}
                    ],
                    "notification": [],
                    "provider": "databricks",
                }
            },
            "databricks_workspace_file": {
                "workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-config-json": {
                    "path": "/.laktory/pipelines/pl-stock-prices-ut-stack/config.json",
                    "source": "./tmp-pl-stock-prices-ut-stack-config.json",
                    "depends_on": ["databricks_pipeline.dlt-custom-name"],
                    "provider": "databricks",
                },
                "workspace-file-laktory-pipelines-pl-stock-prices-ut-stack-requirements-txt": {
                    "path": "/.laktory/pipelines/pl-stock-prices-ut-stack/requirements.txt",
                    "source": "./tmp-pl-stock-prices-ut-stack-requirements.txt",
                    "depends_on": ["databricks_pipeline.dlt-custom-name"],
                    "provider": "databricks",
                },
            },
        },
        "data": {
            "databricks_notebook": {
                "notebook-external": {"path": "/Workspace/external", "format": "SOURCE"}
            },
            "databricks_sql_warehouse": {
                "warehouse-external": {"id": "d2fa41bf94858c4b", "name": None}
            },
        },
    }


@pytest.mark.parametrize("is_full", [True, False])
def test_terraform_plan(monkeypatch, stack, full_stack, is_full):
    if is_full:
        stack = full_stack

    c0 = settings.cli_raise_external_exceptions
    settings.cli_raise_external_exceptions = True

    # Pulumi requires valid Databricks Host and Token and Pulumi Token to run a preview.
    skip_terraform_plan()

    tstack = stack.to_terraform(env_name="dev")
    tstack.init(flags=["-reconfigure"])
    tstack.plan()

    settings.cli_raise_external_exceptions = c0


@pytest.mark.parametrize("is_full", [True, False])
def test_pulumi_preview(monkeypatch, stack, full_stack, is_full):
    if is_full:
        stack = full_stack

    c0 = settings.cli_raise_external_exceptions
    settings.cli_raise_external_exceptions = True

    # Pulumi requires valid Databricks Host and Token and Pulumi Token to run a preview.
    skip_pulumi_preview()

    _stack = stack.to_pulumi("dev")
    _stack.preview(stack="okube/dev")

    settings.cli_raise_external_exceptions = c0


def test_stack_settings():
    current_root = settings.laktory_root
    custom_root = "/custom/path/"

    assert settings.laktory_root != custom_root

    _ = models.Stack(name="one_stack", settings={"laktory_root": custom_root})

    assert settings.laktory_root == custom_root
    settings.laktory_root = current_root


def test_get_env():
    stack = models.Stack(
        name="stack-${vars.v0}-${vars.v1}",
        variables={
            "v0": "value0",
            "v1": "value1",
        },
        environments={
            "dev": {
                "variables": {
                    "v1": "dev",
                }
            },
            "prd": {
                "variables": {
                    "v1": "prd",
                }
            },
        },
    )

    dev = stack.get_env("dev")
    assert dev.name == "stack-${vars.v0}-${vars.v1}"

    dev = stack.get_env("dev").inject_vars()
    assert dev.name == "stack-value0-dev"

    prd = stack.get_env("prd").inject_vars()
    assert prd.name == "stack-value0-prd"
