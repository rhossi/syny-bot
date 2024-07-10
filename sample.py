


import os
from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Database schema
schema = """
CREATE TABLE public.device_twin_variable_histories (
	device_twin_variable_history_id uuid DEFAULT uuid_generate_v4() NOT NULL,
	device_twin_id uuid NOT NULL,
	customer_id uuid NOT NULL,
	device_twin_variable_id uuid NOT NULL,
	"name" varchar NOT NULL,
	category varchar NOT NULL,
	"type" varchar NOT NULL,
	kind varchar NOT NULL,
	value varchar NOT NULL,
	unit varchar NOT NULL,
	meta jsonb NULL,
	created_at timestamp DEFAULT now() NOT NULL,
	alias public."device_twin_variable_histories_alias_enum" NULL,
	CONSTRAINT "PK_709689c38c07ddf16317ce8b8b3" PRIMARY KEY (device_twin_variable_history_id)
);
"""

def generate_sql_query(question):
    prompt = f"""
Given the following database schema:

{schema}

Generate a SQL query to answer this question: "{question}"

Column value is cumulative and should be used to calculate the total value for each name. Group value calculation by name.

For water use filter 'Água Medida' with the column name

Provide only the SQL query, without any explanations or markdown formatting.
If the question cannot be answered with SQL based on the given schema, respond with "CANNOT_GENERATE_QUERY".
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a SQL query generator."},
            {"role": "user", "content": prompt}
        ]
    )

    generated_query = response.choices[0].message.content.strip()

    if generated_query == "CANNOT_GENERATE_QUERY":
        return None
    
    return generated_query

@app.route('/generate_query', methods=['POST'])
def generate_query():
    data = request.json
    question = data.get('question')

    if not question:
        return jsonify({"error": "No question provided"}), 400

    sql_query = generate_sql_query(question)

    if sql_query is None:
        return jsonify({
            "error": "Unable to generate SQL query for the given question",
            "help": "Please ask a question that can be answered using the books and authors database."
        }), 400

    return jsonify({"sql_query": sql_query})

if __name__ == '__main__':
    app.run(debug=True)