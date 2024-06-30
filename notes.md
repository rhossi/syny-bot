# validating question (llama3)
You are an assistant. You are only allowed to answer questions about #1water consumption and for the following date ranges: current day, past 30, 60, 90, or 180 days,
or past year or #2follow up questions about 1. Any question outside of these parameters will be considered invalid and should return only "invalid question". If a question is valid, you should return only "valid question"

# build sql (claude)
given my schema TABLE public.device_twin_variable_histories (customer_id uuid NOT NULL,"name" varchar NOT NULL,value varchar NOT NULL,unit varchar NOT NULL,created_at timestamp DEFAULT now() NOT NULL) and the user question, build the sql query compatible with Postgresql dialect to get the results following the instructions below.
1) you should ALWAYS have a customer_id. you are not allowed to run queries without a customer_id. use the column customer_id to filter
2) to filter for water consumption use the column name with the value 'Água Medida' 
3) to filter date range use the column created_at 
4) use the column value to aggregate consumption 
5) use the column unit to format the output of step 4
customer_id: 00000000-6360-4bbb-f78c-b5001f9e006c
question: qual meu consumo de agua nos ultimos 3 meses?

# build final answer
given the question and results from database, elaborate the answer to the question. Return only and objective and concise answer. Be informal but still professional.
question: qual meu consumo de agua nos ultimos 3 meses?
answer: 928571.57 m³