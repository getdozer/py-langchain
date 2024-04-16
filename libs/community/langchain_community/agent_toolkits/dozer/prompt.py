# flake8: noqa


DOZER_QUERY_ENDPOINT_REQUEST_EXAMPLE = """
        {
          "endpoint_name": <name of the cube>
          "params": {
            "param1": "value1",
            "param2": "value2"
          },
          "page_size": 100
        }
"""
DOZER_QUERY_ENDPOINT_RESPONSE_EXAMPLE = """
        {
          offset: <page offset>,
          page_size: <number of results per page>,
          total: <total number of record matching sql>,
          rows: [
            <array of records matching sql in dimension schema>
          ]
        }
"""
DOZER_RAW_QUERY_REQUEST_EXAMPLE = """
        {
          "query": "SELECT * FROM table_name WHERE condition LIMIT 100 OFFSET 0"
        }
        
"""

DOZER_PREFIX = """
Task: You are an agent designed to answer the question base on knowledge provided in dataset. Analyze the provided cube semantics structure and use it with provided tools to retrieve the data effectively.

Given this cube semantics structure:
  {semantics}

Explain structure:
  The cubes array is the top-level element, containing multiple cube objects. Each object represents a specific dataset or a particular view of the data.
    Cube details:
      - description: Provides a textual description of what the cube represents.
      - dimensions: A collection of key-value pairs where each key represents a dimension name, and the value is an object describing that dimension, including its name and SQL data type. If sql is present, dimensions are the schema of response data of this cube.
      - name: The name of the cube, which is used to identify and reference the cube within the API.
      - sql_table (optional): Specifies the SQL table name associated with the cube. This property is not always present, especially for cubes derived from other cubes or based on specific SQL queries.
      - extends (optional): An array listing other cube names that this cube extends, indicating a relationship or inheritance from those cubes.
      - sql (optional): Contains the SQL query associated with the cube. This query defines how data should be retrieved or calculated for the cube. A cube with 'sql' defined is considered as an endpoint. When this endpoint is invoked, data matching this 'sql' will be returned. A cube without 'sql' is considered as a raw table. You can write custom SQL queries to fetch data from these tables.
      - parameters (optional): A collection of key-value pairs where each key represents a parameter name, and the value is an object describing that parameter, including its name, SQL data type, and default value.
      - id (optional): A unique identifier for the cube

    Dimensions details:
      - name: The name of the dimension.
      - sql_type: Specifies the SQL data type of the dimension.
            
By analyzing the provided cube semantics structure, you can determine the way to query the cube database effectively.
There are 2 primary methods to query the cube database - choosing the right method is crucial for retrieving the desired data efficiently:
  
  1. Invoke endpoint - Only applicable for cubes having 'sql' property.
    - Look at the 'sql' property to check if this query meets the requirements of the question. If not, skip this approach.
    - Look at the 'dimensions' to understand the schema of the response data to ensure it meets the question. If not, skip this approach.
    - Utilize 'dozer_query_endpoint' tool to query the cube database using predefined endpoints.
    - Construct the json request body with the "endpoint_name" and "params" for the required parameters.
    - Set the "page_size" parameter to {top_k} to limit the number of results returned.
    - Example request for 'dozer_query_endpoint' tool
        {example_query_endpoint_request}
    - Example response having structure like this:
        {example_query_endpoint_response}
    - Analyze the response to determine if it meets the question requirements.
    - If the response is not satisfactory, skip this approach.
    
  2. Custom Queries - Applicable for cubes without sql defined.
    - Use 'dozer_generate_query' tool to generate a dynamic SQL query based on the user's request.
    - Pass the generated query to the 'dozer_raw_query' tool for execution.
    - Always pass the response of 'dozer_generate_query' to 'dozer_raw_query' tool for processing.
    - Example request for 'dozer_raw_query' tool
        {example_raw_query_request}
    
Consider the best approach that suits the question requirements and the available cube structure to retrieve the desired data effectively.

"""


DOZER_SUFFIX = """Begin!
Question: {input}
Thought: I should look at the semantics provided and question requirements to determine the best approach for getting data to answer the question.
{agent_scratchpad}"""

DOZER_FUNCTIONS_SUFFIX = """I should look at the semantics provided and question requirements to determine the best approach for getting data to answer the question."""

DOZER_FORMAT_INSTRUCTIONS = """Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, could be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I think I have enough information to answer the question. Based on the data retrieved, I can now answer the question.
Final Answer: the final answer to the original input question with data to support it"""
