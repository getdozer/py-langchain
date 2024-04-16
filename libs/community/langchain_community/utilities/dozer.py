from dataclasses import dataclass
from typing import Dict, List, Optional

import requests
from langchain_core.pydantic_v1 import BaseModel, SecretStr, root_validator
from langchain_core.utils import convert_to_secret_str, get_from_dict_or_env


@dataclass
class EndpointQueryParams:
    endpoint_name: str
    params: Optional[dict] = None


@dataclass
class Dimension:
    name: str
    sql_type: str
    description: Optional[str] = None

    def to_dict(self):
        return {
            "sql_type": self.sql_type,
            "description": self.description,
            "name": self.name,
        }


@dataclass
class Parameter:
    array: bool
    name: str
    param_type: str
    description: Optional[str] = None


@dataclass
class Cube:
    id: str
    description: str
    dimensions: Dict[str, Dimension]
    name: str
    sql_table: Optional[str] = None
    extends: Optional[List[str]] = None
    sql: Optional[str] = None
    params: Optional[List[Parameter]] = None

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "dimensions": {key: value for key, value in self.dimensions.items()},
            "name": self.name,
            "sql_table": self.sql_table,
            "extends": self.extends,
            "sql": self.sql,
            "params": self.params,
        }


# Custom representer for Cube objects
def cube_representer(dumper, data):
    cube_dict = {
        "id": data.id,
        "description": data.description,
        "dimensions": {key: value for key, value in data.dimensions.items()},
        "name": data.name,
        "sql_table": data.sql_table,
        "extends": data.extends,
        "sql": data.sql,
        "params": data.params,
    }
    return dumper.represent_mapping("tag:yaml.org,2002:map", cube_dict)


@dataclass
class Semantics:
    cubes: List[Cube]

    def filter_endpoints(self) -> "Semantics":
        """Filters cubes where the sql attribute is not None."""
        filtered_cubes = [
            cube for cube in self.cubes if getattr(cube, "sql", None) is not None
        ]
        return Semantics(cubes=filtered_cubes)

    def filter_tables(self) -> "Semantics":
        """Filters cubes where the sql attribute is None."""
        filtered_cubes = [cube for cube in self.cubes if "sql" not in cube]
        return Semantics(cubes=filtered_cubes)

    def to_dict(self):
        # convert each cube to dict
        dict_cube = [cube.to_dict() for cube in self.cubes]
        return {"cubes": dict_cube}


class DozerPulseWrapper(BaseModel):
    """Wrapper around Dozer Pulse APIs.

    Example:
      .. code-block:: python

      from langchain_community.utilities import DozerPulseWrapper
      pulse = DozerPulseWrapper()
      pulse.run('semantics')
    """

    api_key: Optional[SecretStr]
    """The API key to use for Dozer Pulse."""

    application_id: Optional[int]
    """Application Id in Dozer Pulse."""

    # base_url: str = "https://api.dev.getdozer.io"
    base_url: str = "http://localhost:8080"
    """The base URL for Dozer Pulse engine."""

    @root_validator()
    def validate_environment(cls, values: Dict) -> Dict:
        """Validate that api key and python package exists in environment."""
        values["api_key"] = convert_to_secret_str(
            get_from_dict_or_env(values, "api_key", "DOZER_API_KEY")
        )
        values["application_id"] = get_from_dict_or_env(
            values, "application_id", "DOZER_APP_ID"
        )

        return values

    def fetch_semantics(self) -> Semantics:
        """Fetch Semanatics for a given application using Dozer Pulse APIs.

        Returns:
          Semantics: An instance of the Semantics data class containing the fetched
                   semantic information as a list of Cube data class instances.

        Raises:
          HTTPError: An error from the requests library if the HTTP request returned
                   an unsuccessful status code.
        """
        headers = self._headers()
        url = f"{self.base_url}/apps/{self.application_id}/semantics"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return Semantics(**data)

    def query_endpoint(self, params: EndpointQueryParams, offset=None) -> dict:
        """
        Send a POST request to the query endpoint with the provided parameters.

        Args:
            params (EndpointQueryParams): The parameters to send with the POST request.

        Returns:
            dict: The JSON response from the server.
        """

        try:
            headers = self._headers()
            url = f"{self.base_url}/apps/{self.application_id}/{params.endpoint_name}?paginate=true&offset={offset or 10}"
            response = requests.post(url, headers=headers, json=params.params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e.response.content)}

    def raw_query(self, raw_sql: str) -> dict:
        """
        Send a POST request to the raw query endpoint with the provided SQL query.

        Args:
            raw_sql (str): The raw SQL query to send.

        Returns:
            dict: The JSON response from the server.
        """
        headers = self._headers()
        url = f"{self.base_url}/apps/{self.application_id}/execute"
        try:
            response = requests.post(url, headers=headers, json={"query": raw_sql})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e.response.content)}

    def _headers(self) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key.get_secret_value()}",
            "Accept": "application/json",
        }
        return headers
