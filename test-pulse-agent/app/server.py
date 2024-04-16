from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from langserve import add_routes
from dozer_pulse_agent import agent_executor as dozer_pulse_agent_executor
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.runnables import RunnableLambda
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain.schema.output_parser import StrOutputParser
from langchain.pydantic_v1 import BaseModel
from typing import Any
import json
import yaml
from langchain_community.chat_models import ChatOllama




app = FastAPI()

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)
class Input(BaseModel):
    semantics: str

def wrapper_init_suggest_chain(_dict):
    semantics_str = _dict["semantics"]
    prompt_suggest_topic = """
  Given semantics cube YAML structure:
    ------------
    ${cubes_yaml}
    ------------
    Structure of the semantics cube:
    Structure of the semantics cube:
        - The YAML structure outlines metadata for two types of data cubes: raw table cubes and predefined SQL query cubes. The specific details of these cubes are described above.
            - Predefined SQL Query Cubes: Cubes with "sql" property .Feature optimized SQL queries for specific analytical tasks. These may need input parameters and support pagination and filtering.
            - Raw Table Cubes: Cubes without "sql" property, Represent raw database tables, useful for constructing custom SQL queries. These cubes can be used to fetch data by writing query for specific analytics tasks.
    
        - Understand that Predefined SQL Query Cubes come with set SQL queries, potentially requiring parameters, and can be used directly to fetch data for specific analytics.
        - Raw Table Cubes are linked to database tables, allowing for custom SQL queries, including joins, to retrieve tailored data sets.
        - To answer questions, you can use Predefined SQL Query Cubes or write custom SQL queries based on Raw Table Cubes. But you cannot do both.
        - Only depending on info semantics cube provides, do not make any assumptions about the  schema or data it could return.
   
    A question can be answered by querying the provided semantics cube if it aligns with the provided semantics cube by checking these two options:
        - Option using raw table cubes: so we dont need to have a predefined query. With these raw tables ${raw_table_ids} then look at their dimensions property, try to convert the question into a SQL query that can be used to fetch data from these tables. SQL query can include any sorting, ordering or agregation method. As long as the question can be answered by the these tables, it is considered relevant.
        - Option using cubes with predefined sql: using one of these cubes with name ${predefined_sql_ids_str}, look at the predefined "sql" property and their dimensions to determine if it can answer the question directly without any modifying or perform any further step. Do not make any assumptions about the data it could return. If something is missing, it is considered irrelevant.
  
   TASK: Can you suggest 7 analysis question that can be answer by provided semantics cube above ?
        - Your anwser should not expose any information about the data or schema of the cube.
        - Your answer should not include any explanation or context.
    """
    llm = ChatOpenAI(temperature=0, model_name="gpt-3.5-turbo-0125")
    # llm = ChatOllama(model="llama2")

    # convert string to semantics object
    semantics_obj = json.loads(semantics_str)
    raw_table = [cube for cube in semantics_obj['cubes'] if not cube.get('sql')]
    predefined_sql = [cube for cube in semantics_obj['cubes'] if cube.get('sql')]
    raw_table_ids = [cube.get('id') for cube in raw_table]
    predefined_sql_ids = [cube.get('id') for cube in predefined_sql]
    predefined_sql_ids_str = ', '.join(predefined_sql_ids)
    yaml_str = yaml.dump(semantics_obj)
    prompt_suggest_topic = prompt_suggest_topic.format(cubes_yaml=yaml_str, raw_table_ids=raw_table_ids, predefined_sql_ids_str=predefined_sql_ids_str)
    prompt = PromptTemplate.from_template(prompt_suggest_topic)
    chain = prompt | llm | StrOutputParser()
    return chain
    
    
    
runable_lambda = RunnableLambda(wrapper_init_suggest_chain)


add_routes(app, dozer_pulse_agent_executor, path="/dozer_pulse_agent")
add_routes(app, runable_lambda.with_types(input_type=Input), path="/suggest_chain")

@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")


# Edit this to add the chain you want to add
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
