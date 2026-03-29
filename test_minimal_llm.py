import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from typing import Optional

load_dotenv()

class OrderExtractionModel(BaseModel):
    customer_name: Optional[str] = None
    referenced_order_id: Optional[str] = None

llm = ChatGoogleGenerativeAI(
    model="gemini-flash-latest",
    google_api_key=os.environ.get("GEMINI_API_KEY"),
    temperature=0
)
extractor = llm.with_structured_output(OrderExtractionModel)

prompt = "Update order CJS-12345: change to velvet."
res = extractor.invoke(prompt)
print(f"RESULT: {res}")
