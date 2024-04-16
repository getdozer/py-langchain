PLAN_OUTPUT_FORMAT = """
```json

    {
      success: true,
      error_reason: "This query is not relevant to the provided data",
      steps: [
            {
                "action": "tool name",
                "description": "description of the task"
                "explanation": "explanation of the task",
            },
            ...
        ]
    }
    
```
"""


TOP_TXNS_REGION = """
SELECT * from users u, count(t.id) as txn_count
join transactions t on t.user_id = u.id
where u.region = {{region}}
group by u.id 
order by txn_count desc limit 20
"""


cube_name = "top_users"
dimension_name = "category"
ENDPOINT_EXAMPLE = f"""
For example: a cube with name ${cube_name} is having the following predefined SQL 
{TOP_TXNS_REGION}.
To get data from this cube, you need to invoke endpoint/{cube_name} with method POST and body as below:
    {{
        "params": {{region: 'USA'}},
        "paginate": true,
        "page_size": 10,
        "offset": 0
    }}

Response will be json object with properties defined in dimensions
"""


RAW_QUERY_EXAMPLE = f"""
For example: You have cubes with names [users, customers, transactions].
        To get data from these cubes, you need to write SQL query to fetch data from these tables.
        For instance, you can write query as below:
            SELECT * FROM {cube_name} WHERE user.{dimension_name} = {{any value base on dimmension type}} LIMIT 10 OFFSET 0
            
            - Replace {{any value base on dimmension type}} with actual value based on dimension type.
            - Using Clickhouse SQL syntax to write query.
            - Get only collumn you need by using SELECT clause.
            - Pagination is supported by using LIMIT and OFFSET in the query.
            - Aggregation can be done by using GROUP BY and aggregate functions.
            - Filtering can be done by using WHERE clause.
            - Sorting can be done by using ORDER BY clause.
    
        Then execute the query to get data from the table by invoking endpoint /execute with method POST and body as below:
        {{
            "query": "your query here",
        }}
        Response will be json object with properties defined in dimensions
"""


DOZER_QUERY_PLAN_PROMPT = """
UNDERSTAND SEMANTICS OF CUBE

Here is the semantics  of the available data in YAML format representing OLAP cubes:
{semantics}

As you can see in the structure, there's 2 kind of cubes:
- Predefined SQL Query Cubes: Cubes with "sql" property. Feature optimized SQL queries for specific analytical tasks. Looking at sql query, you could also undertand the how to data is fetched by that query. These may need input parameters and support pagination and filtering.
    {endpoint_example} 
- Raw Table Cubes: Cubes without "sql" property, Represent raw database tables, useful for constructing custom SQL queries. These cubes can be used to fetch data by writing query for specific analytics tasks.
    {raw_query_example}

Your goal is to understand the semantics of the cube and brokendown the question into smaller tasks to get the data from the cube to answer the question.
 - A task is step invoke one of available tools
 - a planning response if successful is a list of tasks to be able get the data from the cube to answer the question.
 - a planning response if not successful returns success false with a valid reason and empty steps.                      
                      

Available tools:
  {tools_available_description}

Your planning response should be in JSON format with properties as below:
  {format_response}

QUESTION: {question}
Response: response in JSON format as described above
"""


DOZER_GENERATE_QUERY_RESPONSE = """
```json
    {
        "body": {
            "query": "your generated query"
        },
        "path: "execute",
        "description": "description of the query"
        "explanation": "explanation of the query"
    }
```
"""

DOZER_GENERATE_QUERY = """
TABLES STRUCTURE:

{raw_tables_str}

Your task is to generate a valid Clickhouse SQL query to retrieve data from the provided tables.
Follow these steps carefully:

1. Understand the Schema: Examine the schema details for each table. Identify the columns available in each table and their relationships, particularly focusing on common columns that can be used for JOIN operations.
2. Analyze the Query: Review the user's question and determine the data requirements. Identify the tables that need to be queried and the columns necessary to answer the question effectively.
3. Construct the Query: Use Clickhouse SQL syntax to construct the query. Include the necessary columns in the SELECT clause, apply JOIN operations to combine tables, and use WHERE conditions for filtering data.
    - Using Clickhouse SQL syntax to write query
    - Use JOIN to combine data from different tables.
    - Get only column you need by using SELECT clause. Only include columns that relevant to the question and valuable to natural response for user to understand. Aim to minimize the number of selected columns for optimization purposes.
    - Ensure that the selected columns exist in the table from which they are being selected. DO NOT include any columns in the SELECT statement that are not explicitly listed under the table's schema.
    - Pagination is supported by using LIMIT and OFFSET in the query. Let assume that the page_size is 100 and offset is 0.
    - Aggregation can be done by using GROUP BY and aggregate functions.
    - Filtering can be done by using WHERE clause.
    - Sorting can be done by using ORDER BY clause. When sorting by a column that is not directly present in the queried table, make sure to join the relevant tables to access that column.
    - DO NOT include ; at the end of the query.
4. Generate the Query: Based on the analysis and construction steps, generate a valid Clickhouse SQL query that accurately responds to the user's question. Ensure that the query is well-structured, efficient, and provides the necessary data to answer the query effectively.

{examples}


QUESTION: {input}
Response: SQL query as a string without any additional information.
"""
