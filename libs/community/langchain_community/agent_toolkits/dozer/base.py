"""Dozer Pulse agent."""
from __future__ import annotations

import warnings
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Union,
    cast,
)

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.prompts import BasePromptTemplate, PromptTemplate
from langchain_core.prompts.chat import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_openai import ChatOpenAI

from langchain_community.agent_toolkits.dozer.prompt import (
    DOZER_FORMAT_INSTRUCTIONS,
    DOZER_FUNCTIONS_SUFFIX,
    DOZER_PREFIX,
    DOZER_QUERY_ENDPOINT_REQUEST_EXAMPLE,
    DOZER_QUERY_ENDPOINT_RESPONSE_EXAMPLE,
    DOZER_RAW_QUERY_REQUEST_EXAMPLE,
)
from langchain_community.agent_toolkits.dozer.toolkit import DozerPulseToolkit
from langchain_community.tools.dozer.tool import DozerSemanticsTool

if TYPE_CHECKING:
    from langchain.agents.agent import AgentExecutor
    from langchain.agents.agent_types import AgentType
    from langchain_core.callbacks import BaseCallbackManager
    from langchain_core.language_models import BaseLanguageModel
    from langchain_core.tools import BaseTool

    from langchain_community.utilities.dozer import DozerPulseWrapper


def create_dozer_agent_simple(
    api_key: Optional[str] = None,
    application_id: Optional[int] = None,
    verbose: Optional[bool] = False,
    llm: Optional[BaseLanguageModel] = None,
):
    # if api_key is None or application_id is None show error
    if api_key is None or application_id is None:
        warnings.warn("Please provide api_key and application_id to create dozer agent")
        return None
    dozer = DozerPulseWrapper(api_key=api_key, application_id=application_id)
    llm = llm or ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo-0125")
    toolkit = DozerPulseToolkit(dozer=dozer, llm=llm)

    return create_dozer_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=verbose,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    )


def create_dozer_agent(
    llm: BaseLanguageModel,
    toolkit: Optional[DozerPulseToolkit] = None,
    agent_type: Optional[Union[AgentType, Literal["openai-tools"]]] = "openai-tools",
    callback_manager: Optional[BaseCallbackManager] = None,
    prefix: Optional[str] = None,
    suffix: Optional[str] = None,
    format_instructions: Optional[str] = None,
    input_variables: Optional[List[str]] = None,
    top_k: int = 100,
    max_iterations: Optional[int] = 15,
    max_execution_time: Optional[float] = None,
    early_stopping_method: str = "force",
    verbose: bool = False,
    agent_executor_kwargs: Optional[Dict[str, Any]] = None,
    extra_tools: Sequence[BaseTool] = (),
    *,
    dozer: Optional[DozerPulseWrapper] = None,
    prompt: Optional[BasePromptTemplate] = None,
) -> AgentExecutor:
    """Construct a Dozer Pulse agent from an LLM and toolkit or dozer instance."""

    # noqa: E501
    from langchain.agents import (
        create_openai_tools_agent,
        create_react_agent,
    )
    from langchain.agents.agent import (
        AgentExecutor,
        RunnableAgent,
        RunnableMultiActionAgent,
    )
    from langchain.agents.agent_types import AgentType

    if toolkit is None and dozer is None:
        raise ValueError(
            "Must provide exactly one of 'toolkit' or 'dozer'. Received neither."
        )
    if toolkit and dozer:
        raise ValueError(
            "Must provide exactly one of 'toolkit' or 'dozer'. Received both."
        )
    if input_variables:
        kwargs = kwargs or {}
        kwargs["input_variables"] = input_variables

    toolkit = toolkit or DozerPulseToolkit(llm=llm, db=dozer)
    agent_type = agent_type or AgentType.ZERO_SHOT_REACT_DESCRIPTION
    tools = toolkit.get_tools() + list(extra_tools)
    semantics_str = toolkit.fetch_endpoints()
    if prompt is None:
        prefix = prefix or DOZER_PREFIX
        prefix = prefix.format(
            top_k=top_k,
            semantics=semantics_str,
            example_query_endpoint_request=DOZER_QUERY_ENDPOINT_REQUEST_EXAMPLE,
            example_query_endpoint_response=DOZER_QUERY_ENDPOINT_RESPONSE_EXAMPLE,
            example_raw_query_request=DOZER_RAW_QUERY_REQUEST_EXAMPLE,
        )
    else:
        if "top_k" in prompt.input_variables:
            prompt = prompt.partial(top_k=str(top_k))
        if any(key in prompt.input_variables for key in ["semantics"]):
            semantics = toolkit.fetch_endpoints()
            if "semantics" in prompt.input_variables:
                prompt = prompt.partial(semantics=semantics)
                tools = [
                    tool for tool in tools if not isinstance(tool, DozerSemanticsTool)
                ]

    if agent_type == AgentType.ZERO_SHOT_REACT_DESCRIPTION:
        if prompt is None:
            from langchain.agents.mrkl import prompt as react_prompt

            format_instructions = (
                format_instructions or react_prompt.FORMAT_INSTRUCTIONS
            )
            template = "\n\n".join(
                [
                    DOZER_PREFIX,
                    """
                    You have access to the following tools:
                        {tools}
                    """,
                    DOZER_FORMAT_INSTRUCTIONS,
                    react_prompt.SUFFIX,
                ]
            )
            prompt = PromptTemplate.from_template(template)
            prompt = prompt.partial(
                example_query_endpoint_request=DOZER_QUERY_ENDPOINT_REQUEST_EXAMPLE
            )
            prompt = prompt.partial(
                example_query_endpoint_response=DOZER_QUERY_ENDPOINT_RESPONSE_EXAMPLE
            )
            prompt = prompt.partial(
                example_raw_query_request=DOZER_RAW_QUERY_REQUEST_EXAMPLE
            )
            prompt = prompt.partial(top_k=top_k)
            if "semantics" in prompt.input_variables:
                prompt = prompt.partial(semantics=semantics_str)

        agent = RunnableAgent(
            runnable=create_react_agent(llm, tools, prompt),
            input_keys_arg=["input"],
            return_keys_arg=["output"],
            verbose=verbose,
        )

    elif agent_type == "openai-tools":
        if prompt is None:
            prefix = prefix.format(
                example_query_endpoint_request=DOZER_QUERY_ENDPOINT_REQUEST_EXAMPLE
            )
            prefix = prefix.format(
                example_query_endpoint_response=DOZER_QUERY_ENDPOINT_RESPONSE_EXAMPLE
            )
            prefix = prefix.format(
                example_raw_query_request=DOZER_RAW_QUERY_REQUEST_EXAMPLE
            )
            messages = [
                SystemMessage(content=cast(str, prefix)),
                HumanMessagePromptTemplate.from_template("{input}"),
                AIMessage(content=suffix or DOZER_FUNCTIONS_SUFFIX),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
            prompt = ChatPromptTemplate.from_messages(messages)
        agent = RunnableMultiActionAgent(
            runnable=create_openai_tools_agent(llm, tools, prompt),
            input_keys_arg=["input"],
            return_keys_arg=["output"],
            verbose=verbose,
        )

    else:
        raise ValueError(
            f"Agent type {agent_type} not supported at the moment. Must be one of "
            "'openai-tools' or 'zero-shot-react-description'."
        )

    return AgentExecutor(
        name="Dozer Pulse Executor",
        agent=agent,
        tools=tools,
        callback_manager=callback_manager,
        verbose=verbose,
        max_iterations=max_iterations,
        max_execution_time=max_execution_time,
        early_stopping_method=early_stopping_method,
        handle_parsing_errors=True,
        **(agent_executor_kwargs or {}),
    )
