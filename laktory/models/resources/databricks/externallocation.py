import re
from typing import Union
from laktory.models.basemodel import BaseModel
from laktory.models.grants.externallocationgrant import ExternalLocationGrant
from laktory.models.resources.databricks.grants import Grants, GrantsIndividual
from laktory.models.resources.pulumiresource import PulumiResource
from laktory.models.resources.terraformresource import TerraformResource


class ExternalLocationEncryptionDetailsSseEncryptionDetails(BaseModel):
    """
    Attributes
    ----------
    algorith:
    aws_kms_key_arn:
    """

    algorith: str = None
    aws_kms_key_arn: str = None


class ExternalLocationEncryptionDetails(BaseModel):
    """
    Attributes
    ----------
    sse_encryption_details:
    """

    sse_encryption_details: ExternalLocationEncryptionDetailsSseEncryptionDetails = None


class ExternalLocation(BaseModel, PulumiResource, TerraformResource):
    """
    Databricks External Location

    Attributes
    ----------
    access_point:
        The ARN of the s3 access point to use with the external location (AWS).
    comment:
        User-supplied free-form text.
    credential_name:
        Name of the databricks.StorageCredential to use with this external location.
    encryption_details:
        The options for Server-Side Encryption to be used by each Databricks s3 client when connecting to S3 cloud
        storage (AWS).
    force_destroy:
        Destroy external location regardless of its dependents.
    force_update:
        Update external location regardless of its dependents.
    grants:
        List of grants operating on the external location.        
    individual_grants:
        List of grants operating on the external location. Different from `grants` in that
        it does not remove grants for other principals not specified in the list.             
    metastore_id:
        Metastore ID
    name:
        Name of External Location, which must be unique within the databricks_metastore. Change forces creation of a new
        resource.
    owner:
        Username/groupname/sp application_id of the external location owner.
    read_only:
        Indicates whether the external location is read-only.
    skip_validation:
        Suppress validation errors if any & force save the external location
    url:
        Path URL in cloud storage, of the form: s3://[bucket-host]/[bucket-dir] (AWS), abfss://[user]@[host]/[path]
        (Azure), gs://[bucket-host]/[bucket-dir] (GCP).

    Examples
    --------
    ```py
    ```
    """

    access_point: str = None
    comment: str = None
    credential_name: str = None
    encryption_details: ExternalLocationEncryptionDetails = None
    force_destroy: bool = None
    force_update: bool = None
    grants: list[ExternalLocationGrant] = None
    individual_grants: list[ExternalLocationGrant] = None
    metastore_id: str = None
    name: str = None
    owner: str = None
    read_only: bool = None
    skip_validation: bool = None
    url: str = None

    # ----------------------------------------------------------------------- #
    # Resource Properties                                                     #
    # ----------------------------------------------------------------------- #
    @property
    def additional_core_resources(self) -> list[PulumiResource]:
        """
        - external location grants
        """
        resources = []

        # External Location Grants
        if self.grants:
            resources += Grants(
                resource_name=f"grants-{self.resource_name}",
                storage_credential=f"${{resources.{self.resource_name}.name}}",
                grants=[{"principal": g.principal, "privileges": g.privileges} for g in self.grants]
            ).core_resources

        if self.individual_grants:
            for g in self.individual_grants:
                for idx, g in enumerate(self.individual_grants):
                    principal = str(idx) if re.match(r"\$\{resources\.(.*?)\}", g.principal) else g.principal
                    resources += GrantsIndividual(
                        resource_name=f"grant-{self.resource_name}-{principal}",
                        storage_credential=f"${{resources.{self.resource_name}.name}}",
                        principal=g.principal,
                        privileges=g.privileges,
                    ).core_resources  

        return resources

    @property
    def resource_key(self) -> str:
        """External location full name"""
        return self.name

    @property
    def additional_core_resources(self) -> list[PulumiResource]:
        """
        - external location grants
        """
        resources = []

        # Schema grants
        if self.grants or self.grant:
            if self.grants:
                resources += Grants(
                    resource_name=f"grants-{self.resource_name}",
                    external_location=f"${{resources.{self.resource_name}.name}}",
                    grants=[
                        {"principal": g.principal, "privileges": g.privileges}
                        for g in self.grants
                    ],
                ).core_resources
            else:
                # if grant is provided, use it instead of grants (for principal specific grants)
                resources += Grants(
                    resource_name=f"grants-{self.resource_name}",
                    external_location=self.name,
                    principal=self.grant.principal,
                    privileges=self.grant.privileges,
                ).core_resources

        return resources

    @property
    def resource_key(self) -> str:
        """External location full name"""
        return self.name

    @property
    def additional_core_resources(self) -> list[PulumiResource]:
        """
        - external location grants
        """
        resources = []

        # External location grants
        if self.grants:
            resources += Grants(
                resource_name=f"grants-{self.resource_name}",
                external_location=f"${{resources.{self.resource_name}.name}}",
                grants=[{"principal": g.principal, "privileges": g.privileges} for g in self.grants]
            ).core_resources

        if self.individual_grants:
            for g in self.individual_grants:
                for idx, g in enumerate(self.individual_grants):
                    principal = str(idx) if re.match(r"\$\{resources\.(.*?)\}", g.principal) else g.principal
                    resources += GrantsIndividual(
                        resource_name=f"grant-{self.resource_name}-{principal}",
                        external_location=f"${{resources.{self.resource_name}.name}}",
                        principal=g.principal,
                        privileges=g.privileges,
                    ).core_resources

        return resources

    # ----------------------------------------------------------------------- #
    # Pulumi Properties                                                       #
    # ----------------------------------------------------------------------- #

    @property
    def pulumi_resource_type(self) -> str:
        return "databricks:ExternalLocation"
    
    @property
    def pulumi_excludes(self) -> Union[list[str], dict[str, bool]]:
        return [ "grants", "individual_grants"]
    # ----------------------------------------------------------------------- #
    # Terraform Properties                                                    #
    # ----------------------------------------------------------------------- #

    @property
    def terraform_resource_type(self) -> str:
        return "databricks_external_location"

    @property
    def terraform_excludes(self) -> Union[list[str], dict[str, bool]]:
        return self.pulumi_excludes
