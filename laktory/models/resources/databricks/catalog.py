import re
from typing import Literal
from typing import Union

from pydantic import Field
from pydantic import model_validator

from laktory.models.basemodel import BaseModel
from laktory.models.grants.cataloggrant import CatalogGrant
from laktory.models.resources.baseresource import ResourceLookup
from laktory.models.resources.databricks.grants import Grants, GrantsIndividual
from laktory.models.resources.databricks.schema import Schema
from laktory.models.resources.pulumiresource import PulumiResource
from laktory.models.resources.terraformresource import TerraformResource


class CatalogLookup(ResourceLookup):
    """
    Attributes
    ----------
    name:
        Catalog name
    """

    name: str = Field(serialization_alias="id")


class Catalog(BaseModel, PulumiResource, TerraformResource):
    """
    A catalog is the first layer of Unity Catalog’s three-level namespace. It’s
    used to organize your data assets.

    Attributes
    ----------
    comment:
        Text description of the catalog
    force_destroy:
        If `True` catalog can be deleted, even when not empty
    grants:
        List of grants operating on the catalog
    individual_grants:
        List of grants operating on the catalog. Different from `grants` in that
        it does not remove grants for other principals not specified in the list.      
    isolation_mode:
        Whether the catalog is accessible from all workspaces or a specific set
        of workspaces. Can be ISOLATED or OPEN. Setting the catalog to ISOLATED
        will automatically allow access from the current workspace.
    lookup_existing:
        Specifications for looking up existing resource. Other attributes will
        be ignored.
    name:
        Name of the catalog
    owner:
        User/group/service principal name of the catalog owner
    schemas:
        List of schemas stored in the catalog
    storage_root:
        Managed location of the catalog. Location in cloud storage where data
        for managed tables will be stored. If not specified, the location will
        default to the metastore root location.

    Examples
    --------
    ```py
    from laktory import models

    catalog = models.resources.databricks.Catalog(
        name="dev",
        grants=[
            {"principal": "account users", "privileges": ["USE_CATALOG", "USE_SCHEMA"]}
        ],
        schemas=[
            {
                "name": "engineering",
                "grants": [
                    {"principal": "domain-engineering", "privileges": ["SELECT"]}
                ],
            },
            {
                "name": "sources",
                "volumes": [
                    {
                        "name": "landing",
                        "volume_type": "EXTERNAL",
                        "grants": [
                            {
                                "principal": "account users",
                                "privileges": ["READ_VOLUME"],
                            },
                            {
                                "principal": "role-metastore-admins",
                                "privileges": ["WRITE_VOLUME"],
                            },
                        ],
                    },
                ],
            },
        ],
    )
    ```

    References
    ----------

    * [Databricks Unity Catalog](https://docs.databricks.com/en/data-governance/unity-catalog/index.html#catalogs)
    * [Pulumi Databricks Catalog](https://www.pulumi.com/registry/packages/databricks/api-docs/catalog/)
    """

    comment: Union[str, None] = None
    force_destroy: bool = True
    grant: CatalogGrant = None
    grants: list[CatalogGrant] = None
    individual_grants: list[CatalogGrant] = None
    isolation_mode: Literal["OPEN", "ISOLATED"] = "OPEN"
    lookup_existing: CatalogLookup = Field(None, exclude=True)
    name: str
    owner: str = None
    schemas: list[Schema] = []
    storage_root: str = None

    @model_validator(mode="after")
    def assign_name(self):
        for schema in self.schemas:
            schema.catalog_name = self.name
            schema.assign_name()

        return self

    # ----------------------------------------------------------------------- #
    # Computed fields                                                         #
    # ----------------------------------------------------------------------- #

    @property
    def full_name(self) -> str:
        """Full name of the catalog `{catalog_name}`"""
        return self.name

    # ----------------------------------------------------------------------- #
    # Resource Properties                                                     #
    # ----------------------------------------------------------------------- #

    @property
    def additional_core_resources(self) -> list[PulumiResource]:
        """
        - catalog grants
        - schemas resources
        """
        resources = []
       
        # Catalog grants
        
        if self.grants:
            resources += Grants(
                resource_name=f"grants-{self.resource_name}",
                catalog=f"${{resources.{self.resource_name}.id}}",
                grants=[{"principal": g.principal, "privileges": g.privileges} for g in self.grants]
            ).core_resources

        if self.individual_grants:
            for g in self.individual_grants:
                for idx, g in enumerate(self.individual_grants):
                    principal = str(idx) if re.match(r"\$\{resources\.(.*?)\}", g.principal) else g.principal
                    resources += GrantsIndividual(
                        resource_name=f"grant-{self.resource_name}-{principal}",
                        metastore=f"${{resources.{self.resource_name}.id}}",
                        principal=g.principal,
                        privileges=g.privileges,
                    ).core_resources

        # Catalog schemas
        if self.schemas:
            for s in self.schemas:
                resources += s.core_resources

        return resources

    # ----------------------------------------------------------------------- #
    # Pulumi Properties                                                       #
    # ----------------------------------------------------------------------- #

    @property
    def pulumi_resource_type(self) -> str:
        return "databricks:Catalog"

    @property
    def pulumi_excludes(self) -> Union[list[str], dict[str, bool]]:
        return ["schemas", "is_unity", "grants", "individual_grants"]

    # ----------------------------------------------------------------------- #
    # Terraform Properties                                                    #
    # ----------------------------------------------------------------------- #

    @property
    def terraform_resource_type(self) -> str:
        return "databricks_catalog"

    @property
    def terraform_excludes(self) -> Union[list[str], dict[str, bool]]:
        return self.pulumi_excludes
