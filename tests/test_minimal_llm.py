import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from typing import Literal

load_dotenv()

class TestModel(BaseModel):
    answer: str = Field(..., description="A simple answer.")
    choice: Literal["A", "B"] = Field(..., description="Choose A or B.")

llm = ChatGoogleGenerativeAI(
    model="gemini-flash-latest",
    google_api_key=os.environ.get("GEMINI_API_KEY")
)
structured_llm = llm.with_structured_output(TestModel)

try:
    response = structured_llm.invoke("What is 1+1?")
    print(f"Response: {response}")
except Exception as e:
    print(f"Error: {e}")
