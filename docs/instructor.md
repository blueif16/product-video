Instructor: Structured Outputs for LLMs
Get reliable JSON from any LLM. Built on Pydantic for validation, type safety, and IDE support.

import instructor
from pydantic import BaseModel


# Define what you want
class User(BaseModel):
    name: str
    age: int


# Extract it from natural language
client = instructor.from_provider("openai/gpt-4o-mini")
user = client.chat.completions.create(
    response_model=User,
    messages=[{"role": "user", "content": "John is 25 years old"}],
)

print(user)  # User(name='John', age=25)
That's it. No JSON parsing, no error handling, no retries. Just define a model and get structured data.

PyPI Downloads GitHub Stars Discord Twitter

Use Instructor for fast extraction, reach for PydanticAI when you need agents. Instructor keeps schema-first flows simple and cheap. If your app needs richer agent runs, built-in observability, or shareable traces, try PydanticAI. PydanticAI is the official agent runtime from the Pydantic team, adding typed tools, replayable datasets, evals, and production dashboards while using the same Pydantic models. Dive into the PydanticAI docs to see how it extends Instructor-style workflows.

Why Instructor?
Getting structured data from LLMs is hard. You need to:

Write complex JSON schemas
Handle validation errors
Retry failed extractions
Parse unstructured responses
Deal with different provider APIs
Instructor handles all of this with one simple interface:

Without Instructor	With Instructor
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "..."}],
    tools=[
        {
            "type": "function",
            "function": {
                "name": "extract_user",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"},
                    },
                },
            },
        }
    ],
)

# Parse response
tool_call = response.choices[0].message.tool_calls[0]
user_data = json.loads(tool_call.function.arguments)

# Validate manually
if "name" not in user_data:
    # Handle error...
    pass
client = instructor.from_provider("openai/gpt-4")

user = client.chat.completions.create(
    response_model=User,
    messages=[{"role": "user", "content": "..."}],
)

# That's it! user is validated and typed
Install in seconds
pip install instructor
Or with your package manager:

uv add instructor
poetry add instructor
Works with every major provider
Use the same code with any LLM provider:

# OpenAI
client = instructor.from_provider("openai/gpt-4o")

# Anthropic
client = instructor.from_provider("anthropic/claude-3-5-sonnet")

# Google
client = instructor.from_provider("google/gemini-pro")

# Ollama (local)
client = instructor.from_provider("ollama/llama3.2")

# With API keys directly (no environment variables needed)
client = instructor.from_provider("openai/gpt-4o", api_key="sk-...")
client = instructor.from_provider("anthropic/claude-3-5-sonnet", api_key="sk-ant-...")
client = instructor.from_provider("groq/llama-3.1-8b-instant", api_key="gsk_...")

# All use the same API!
user = client.chat.completions.create(
    response_model=User,
    messages=[{"role": "user", "content": "..."}],
)
Production-ready features
Automatic retries
Failed validations are automatically retried with the error message:

from pydantic import BaseModel, field_validator


class User(BaseModel):
    name: str
    age: int

    @field_validator('age')
    def validate_age(cls, v):
        if v < 0:
            raise ValueError('Age must be positive')
        return v


# Instructor automatically retries when validation fails
user = client.chat.completions.create(
    response_model=User,
    messages=[{"role": "user", "content": "..."}],
    max_retries=3,
)
Streaming support
Stream partial objects as they're generated:

from instructor import Partial

for partial_user in client.chat.completions.create(
    response_model=Partial[User],
    messages=[{"role": "user", "content": "..."}],
    stream=True,
):
    print(partial_user)
    # User(name=None, age=None)
    # User(name="John", age=None)
    # User(name="John", age=25)
Nested objects
Extract complex, nested data structures:

from typing import List


class Address(BaseModel):
    street: str
    city: str
    country: str


class User(BaseModel):
    name: str
    age: int
    addresses: List[Address]


# Instructor handles nested objects automatically
user = client.chat.completions.create(
    response_model=User,
    messages=[{"role": "user", "content": "..."}],
)
Used in production by
Trusted by over 100,000 developers and companies building AI applications:

3M+ monthly downloads
10K+ GitHub stars
1000+ community contributors
Companies using Instructor include teams at OpenAI, Google, Microsoft, AWS, and many YC startups.

Get started
Basic extraction
Extract structured data from any text:

from pydantic import BaseModel
import instructor

client = instructor.from_provider("openai/gpt-4o-mini")


class Product(BaseModel):
    name: str
    price: float
    in_stock: bool


product = client.chat.completions.create(
    response_model=Product,
    messages=[{"role": "user", "content": "iPhone 15 Pro, $999, available now"}],
)

print(product)
# Product(name='iPhone 15 Pro', price=999.0, in_stock=True)