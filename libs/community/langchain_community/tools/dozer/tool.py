"""Tool for the Dozer Pulse"""

import json
from typing import Any, Dict, Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.callbacks.manager import AsyncCallbackManagerForToolRun
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.prompts.prompt import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, Field, root_validator
from langchain_core.tools import BaseTool

from langchain_community.utilities.dozer import (
    DozerPulseWrapper,
    EndpointQueryParams,
    Semantics,
)

from .prompt import (
    DOZER_GENERATE_QUERY,
    DOZER_GENERATE_QUERY_RESPONSE,
    DOZER_QUERY_PLAN_PROMPT,
    ENDPOINT_EXAMPLE,
    PLAN_OUTPUT_FORMAT,
    RAW_QUERY_EXAMPLE,
)


class DozerRawQueryInput(BaseModel):
    query: str = Field(..., description="should be a valid SQL")


class DozerRawQueryTool(BaseTool):
    """Use this tool to execute a raw sql query to get data"""

    name: str = "dozer_raw_query"
    description: str = """
        Use this tool to execute a raw sql query to get data.
        Input should be a valid SQL query."""
    dozer: DozerPulseWrapper
    args_schema: Type[BaseModel] = DozerRawQueryInput

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the DozerRawQueryTool"""

        query = query.strip()
        try:
            query_parsed = json.loads(query.replace("\n", " "))
            if isinstance(query_parsed, dict):
                if "query" in query_parsed:
                    query = query_parsed["query"]
        except:
            pass
        result = self.dozer.raw_query(query)
        # return stringify result
        return json.dumps(result)
        return self.dozer.raw_query(query)


class DozerQueryEndpointInput(BaseModel):
    params: EndpointQueryParams | str = Field(..., description="")


class DozerQueryEndpointTool(BaseTool):
    """Use this tool to get data from an endpoint"""

    name: str = "dozer_query_endpoint"
    description: str = (
        "Use this tool to get data from an endpoint"
        "Input to this tool is a map {{'endpoint_name': endpoint_name, 'params': 'parameters'}}"
        "endpoint_name is the available endpoint_name"
        "params are parameters defined on that endpoint"
    )
    dozer: DozerPulseWrapper
    args_schema: Type[BaseModel] = DozerQueryEndpointInput

    def _run(
        self,
        params: EndpointQueryParams | str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the DozerQueryEndpointTool."""
        # check type of params, if it is string, parse it to json and convert to EndpointQueryParams
        if isinstance(params, str):
            # Replace single quotes with double quotes
            params = params.replace("'", '"')
            json_params = json.loads(params)
            params = EndpointQueryParams(**json_params)
        # check if params is EndpointQueryParams
        if not isinstance(params, EndpointQueryParams):
            raise ValueError("params should be of type EndpointQueryParams")
        query_result = self.dozer.query_endpoint(params=params)
        return json.dumps(query_result["rows"])


class DozerSemanticsTool(BaseTool):
    """Tool that fetches semantics of an application."""

    name: str = "dozer_semantics"
    description: str = "Fetch semantics of this application"
    dozer: DozerPulseWrapper

    def _run(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        return self.dozer.fetch_semantics()


class DozerGenerateQueryInput(BaseModel):
    input: str = Field(
        ..., description="input should be a request from user in plain text."
    )


class DozerGenerateSqlQueryTool(BaseTool):
    """Use this tool generate a valid SQL query based on user's request and provided semantics cube."""

    name: str = "dozer_generate_query"
    description: str = (
        "Use this tool generate a valid SQL query based on user's request and provided semantics cube.",
        "Input should be a request from user in plain text.",
    )
    semantics: Semantics
    llm: BaseLanguageModel
    llm_chain: Any = Field(init=False)
    args_schema: Type[BaseModel] = DozerGenerateQueryInput

    @root_validator(pre=True)
    def initialize_llm_chain(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if not values["semantics"]:
            raise "semantics is expected"
        semantics: Semantics = values["semantics"]
        raw_tables_str = DozerGenerateSqlQueryTool.get_raw_tables_str(semantics)
        examples_str = DozerGenerateSqlQueryTool.get_sql_example(semantics)

        if "llm_chain" not in values:
            from langchain.chains.llm import LLMChain

            values["llm_chain"] = LLMChain(
                llm=values.get("llm"),
                prompt=PromptTemplate(
                    template=DOZER_GENERATE_QUERY,
                    input_variables=["input"],
                    partial_variables={
                        "format_response": DOZER_GENERATE_QUERY_RESPONSE,
                        "raw_tables_str": raw_tables_str,
                        "examples": examples_str,
                    },
                ),
            )
        return values

    def get_raw_tables_str(semantics: Semantics) -> str:
        """Return raw tables string."""
        raw_cubes = semantics.filter_tables()
        raw_table_cubes = raw_cubes.cubes
        raw_tables_str = ""
        for cube in raw_table_cubes:
            table_description = cube["description"] if "description" in cube else ""
            raw_tables_str += format(f"Name: {cube['sql_table']}\n")
            raw_tables_str += format(f"Description: {table_description}\n")
            raw_tables_str += format("Columns: \n")
            # get keys of dictionary
            dimensions = cube["dimensions"]
            keys = dimensions.keys()
            for key in keys:
                description = (
                    dimensions[key]["description"]
                    if "description" in dimensions[key]
                    else ""
                )
                raw_tables_str += format(
                    f"    {key} {dimensions[key]['sql_type']}    {description} \n"
                )
            raw_tables_str += format("==============================\n")
        return raw_tables_str

    def get_sql_example(semantics: Semantics) -> str:
        """Return sql example."""
        endpoints = semantics.filter_endpoints().cubes
        sql_example = ""
        for endpoint in endpoints:
            if "sql" in endpoint and "description" in endpoint:
                sql_example += format(f"QUESTION: {endpoint['description']}\n")
                sql_example += format(f"Response: {endpoint['sql']}\n")
                sql_example += format("\n")
        return sql_example

    def _run(
        self,
        input: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the LLM to check the query."""
        result = self.llm_chain.predict(
            input=input,
            callbacks=run_manager.get_child() if run_manager else None,
        )
        return result

    async def _arun(
        self,
        input: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        return await self.llm_chain.apredict(
            input=input,
            callbacks=run_manager.get_child() if run_manager else None,
        )


class DozerQueryPlanTool(BaseTool):
    """Planning a process to get data to answer the question."""

    name: str = "dozer_plan"
    description: str = (
        "A wrapper around Dozer Pulse Semantic APIs."
        "Useful for when you need to query your data"
        "imported into Pulse environment"
        "Input should be a query related to your data."
    )
    template: str = DOZER_QUERY_PLAN_PROMPT
    llm: BaseLanguageModel
    llm_chain: Any = Field(init=False)

    @root_validator(pre=True)
    def initialize_llm_chain(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if "llm_chain" not in values:
            from langchain.chains.llm import LLMChain

            values["llm_chain"] = LLMChain(
                llm=values.get("llm"),
                prompt=PromptTemplate(
                    template=DOZER_QUERY_PLAN_PROMPT,
                    input_variables=["query"],
                    partial_variables={
                        "format_response": PLAN_OUTPUT_FORMAT,
                        "endpoint_example": ENDPOINT_EXAMPLE,
                        "raw_query_example": RAW_QUERY_EXAMPLE,
                    },
                ),
            )

        if values["llm_chain"].prompt.input_variables != ["query"]:
            raise ValueError(
                "LLM chain for DozerQueryTool must have input variables ['query']"
            )

        return values

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the LLM to check the query."""
        return self.llm_chain.predict(
            query=query,
            callbacks=run_manager.get_child() if run_manager else None,
        )

    async def _arun(
        self,
        query: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        return await self.llm_chain.apredict(
            query=query,
            callbacks=run_manager.get_child() if run_manager else None,
        )
