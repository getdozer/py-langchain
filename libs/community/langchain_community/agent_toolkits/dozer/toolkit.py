"""Toolkit for interacting with Dozer Pulse APIs."""
from typing import Dict, List, Optional

import yaml
from langchain_core.language_models import BaseLanguageModel
from langchain_core.pydantic_v1 import Field, root_validator

from langchain_community.agent_toolkits.base import BaseToolkit
from langchain_community.tools import BaseTool
from langchain_community.tools.dozer.tool import (
    DozerGenerateSqlQueryTool,
    DozerQueryEndpointTool,
    DozerRawQueryTool,
)
from langchain_community.utilities.dozer import (
    Cube,
    Dimension,
    DozerPulseWrapper,
    Semantics,
)


class DozerPulseToolkit(BaseToolkit):
    """Toolkit for querying Dozer Pulse Applications."""

    dozer: DozerPulseWrapper = Field(exclude=True)
    llm: BaseLanguageModel = Field(exclude=True)
    semantics: Optional[Semantics] = Field(exclude=True)

    class Config:
        """Configuration for this pydantic object."""

        arbitrary_types_allowed = True

    @root_validator()
    def validate_environment(cls, values: Dict) -> Dict:
        """Initialize semantics"""

        if not values["semantics"]:
            dozer: DozerPulseWrapper = values["dozer"]
            semantics: Semantics = dozer.fetch_semantics()
            values["semantics"] = semantics
        return values

    def get_tools(self) -> List[BaseTool]:
        """Get the tools in the toolkit."""
        generate_tool = DozerGenerateSqlQueryTool(
            llm=self.llm, semantics=self.semantics
        )
        query_endpoint_tool = DozerQueryEndpointTool(dozer=self.dozer)
        raw_query_tool = DozerRawQueryTool(dozer=self.dozer)

        return [generate_tool, query_endpoint_tool, raw_query_tool]

    def fetch_endpoints(self) -> str:
        """Return semantics for endpoints."""
        semantics = self.semantics.filter_endpoints()
        yaml.add_representer(Semantics, DozerPulseToolkit.dict_representer)
        yaml.add_representer(Cube, DozerPulseToolkit.dict_representer)
        yaml.add_representer(Dimension, DozerPulseToolkit.dict_representer)
        return yaml.dump(semantics)

    def fetch_tables(self) -> str:
        """Return semantics for raw_tables."""
        semantics = self.semantics.filter_tables()
        yaml.add_representer(Cube, DozerPulseToolkit.dict_representer)
        yaml.add_representer(Dimension, DozerPulseToolkit.dict_representer)

        return yaml.dump(semantics.cubes)

    def semantics_yaml_str(semantics: Semantics) -> str:
        yaml.add_representer(Semantics, DozerPulseToolkit.dict_representer)
        # yaml.add_representer(Cube, DozerPulseToolkit.dict_representer)
        yaml.add_representer(Dimension, DozerPulseToolkit.dict_representer)
        return yaml.dump(semantics)

    def dict_representer(dumper, data):
        cube_dict = data.to_dict()
        return dumper.represent_mapping("tag:yaml.org,2002:map", cube_dict)
