"""Tool for the Dozer Pulse"""

from dataclasses import Field
from typing import Any, Dict, Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.callbacks.manager import AsyncCallbackManagerForToolRun
from langchain_core.language_models.base import BaseLanguageModel
from langchain_core.prompts.prompt import PromptTemplate
from langchain_core.pydantic_v1 import BaseModel, root_validator
from langchain_core.tools import BaseTool

from langchain_community.utilities.dozer import DozerPulseWrapper

from .prompt import (
    DOZER_QUERY_PLAN_PROMPT,
    ENDPOINT_EXAMPLE,
    PLAN_OUTPUT_FORMAT,
    RAW_QUERY_EXAMPLE,
)


class DozerRawQueryInput(BaseModel):
    query: str = Field(..., description="should be a user input")


class DozerRawQueryTool(BaseTool):
    """Tool that executes a raw query using Dozer Pulse APIs."""

    name: str = "dozer_raw_query"
    description: str = "Input is a SQL query"
    dozer: DozerPulseWrapper
    args_schema: Type[BaseModel] = DozerRawQueryInput

    def _run(
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        return self.dozer.raw_query(query)


class DozerQueryEndpointInput(BaseModel):
    endpoint_name: str = Field(..., description="Name of the endpoint")
    params: dict = Field(..., description="parameters")


class DozerQueryEndpointTool(BaseTool):
    """Tool that queries a Dozer Endpoint."""

    name: str = "dozer_query_endpoint"
    description: str = "Input is an endpoint_name and params that the endpoint expects"
    dozer: DozerPulseWrapper
    args_schema: Type[BaseModel] = DozerQueryEndpointInput

    def _run(
        self,
        endpoint_name: str,
        params: Optional[dict] = None,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        """Use the tool."""
        return self.dozer.query_endpoint(endpoint_name=endpoint_name, params=params)


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


# class DozerGenerateSqlQueryTool(BaseTool):
#     """Use an LLM to generate a valid SQL query"""

#     name: str = "dozer_generate_query"
#     description: str = (
#         "Use this tool generate a valid SQL query to be executed raw using Dozer APIs"
#     )

#     @root_validator(pre=True)
#     def initialize_llm_chain(cls, values: Dict[str, Any]) -> Dict[str, Any]:
#         if "llm_chain" not in values:
#             from langchain.chains.llm import LLMChain

#             values["llm_chain"] = LLMChain(
#                 llm=values.get("llm"),
#                 prompt=PromptTemplate(
#                     template=DOZER_GENERATE_QUERY,
#                     input_variables=["query"],
#                     partial_variables={
#                         "format_response": DOZER_GENERATE_QUERY_RESPONSE,
#                     },
#                 ),
#             )

#         if values["llm_chain"].prompt.input_variables != ["query"]:
#             raise ValueError(
#                 "LLM chain for DozerQueryTool must have input variables ['query']"
#             )

#         return values

#     def _run(
#         self,
#         query: str,
#         run_manager: Optional[CallbackManagerForToolRun] = None,
#     ) -> str:
#         """Use the LLM to check the query."""
#         return self.llm_chain.predict(
#             query=query,
#             dialect=self.db.dialect,
#             callbacks=run_manager.get_child() if run_manager else None,
#         )

#     async def _arun(
#         self,
#         query: str,
#         run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
#     ) -> str:
#         return await self.llm_chain.apredict(
#             query=query,
#             dialect=self.db.dialect,
#             callbacks=run_manager.get_child() if run_manager else None,
#         )


class DozerQueryPlanTool(BaseTool):
    """Use an LLM to call Dozer Pulse APIs"""

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
            dialect=self.db.dialect,
            callbacks=run_manager.get_child() if run_manager else None,
        )

    async def _arun(
        self,
        query: str,
        run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
    ) -> str:
        return await self.llm_chain.apredict(
            query=query,
            dialect=self.db.dialect,
            callbacks=run_manager.get_child() if run_manager else None,
        )
