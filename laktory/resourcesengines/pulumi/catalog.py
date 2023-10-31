from typing import Union

import pulumi
import pulumi_databricks as databricks
from laktory.resourcesengines.pulumi.base import PulumiResourcesEngine
from laktory.models.sql.catalog import Catalog

from laktory._logger import get_logger

logger = get_logger(__name__)


class PulumiCatalog(PulumiResourcesEngine):
    @property
    def provider(self):
        return "databricks"

    def __init__(
        self,
        name=None,
        catalog: Catalog = None,
        opts=None,
    ):
        if name is None:
            name = f"catalog-{catalog.full_name}"
        super().__init__(self.t, name, {}, opts)

        opts = pulumi.ResourceOptions(parent=self)

        # Catalog
        self.catalog = databricks.Catalog(
            f"catalog-{catalog.full_name}",
            opts=opts,
            **catalog.model_pulumi_dump(),
        )

        # Grants
        if catalog.grants:
            self.grants = databricks.Grants(
                f"grants-catalog-{catalog.full_name}",
                catalog=self.catalog.name,
                grants=[
                    databricks.GrantsGrantArgs(
                        principal=g.principal, privileges=g.privileges
                    )
                    for g in catalog.grants
                ],
                opts=opts,
            )

        # Schemas
        if catalog.schemas:
            for s in catalog.schemas:
                s.vars = catalog.vars
                s._resources = s.deploy_with_pulumi(
                    opts=pulumi.ResourceOptions(parent=self.catalog)
                )