from typing import Literal
from typing import Union

from laktory.models.basemodel import BaseModel
from laktory.models.resources.pulumiresource import PulumiResource
from laktory.models.resources.terraformresource import TerraformResource


# class CatalogLookup(ResourceLookup):
#     """
#     Attributes
#     ----------
#     name:
#         Catalog name
#     """

#     name: str = Field(serialization_alias="id")


class AzureStorageContainer(BaseModel, PulumiResource, TerraformResource):
    name: str             
    storage_account_id: str
    default_encryption_scope: str = None 
    encryption_scope_override_enabled: str = None
    container_access_type: Literal["blob", "container", "private"] = "private"
    metadata: dict[str, str] = None

    # ----------------------------------------------------------------------- #
    # Computed fields                                                         #
    # ----------------------------------------------------------------------- #

    @property
    def full_name(self) -> str:
        """Full name of the container `{container_name}`"""
        return self.name

    # ----------------------------------------------------------------------- #
    # Resource Properties                                                     #
    # ----------------------------------------------------------------------- #

    @property
    def additional_core_resources(self) -> list[PulumiResource]:
        """
        """
        resources = []

        return resources

    # ----------------------------------------------------------------------- #
    # Pulumi Properties                                                       #
    # ----------------------------------------------------------------------- #

    @property
    def pulumi_resource_type(self) -> str:
        return "azure:storage:Container"

    @property
    def pulumi_excludes(self) -> Union[list[str], dict[str, bool]]:
        return []

    # ----------------------------------------------------------------------- #
    # Terraform Properties                                                    #
    # ----------------------------------------------------------------------- #

    @property
    def terraform_resource_type(self) -> str:
        return "azurerm_storage_container"

    @property
    def terraform_excludes(self) -> Union[list[str], dict[str, bool]]:
        return self.pulumi_excludes
