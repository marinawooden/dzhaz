from dotenv import load_dotenv
import sys
import pinecone
import os
from openai import OpenAI
import streamlit as st

load_dotenv()

# api keys
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
PINECONE_API_ENV = "gcp-starter"


# pinecone index init
pinecone.init(
    api_key=PINECONE_API_KEY,  # find at app.pinecone.io
    environment=PINECONE_API_ENV
)

index = pinecone.Index("dzhaz-bot")

print(OPENAI_API_KEY)
# OpenAI Client
client = OpenAI(api_key=OPENAI_API_KEY)

# other info
model_name = 'text-embedding-ada-002'

# Bot context
bot_context = "Recommend music based on the query"

def main():
  try:
    # initialize bot
    result = query_collection("Hello this is my prompt")
    print(result)
  except Exception as e:
    print('\033[91m' + "An error occurred: " + str(e))

def query_collection(query=False):
  if not query:
    raise Exception("Please provide a prompt!")

  query_embedding = client.embeddings.create(input=query, model=model_name)
  query_embedding = query_embedding.data[0].embedding
  
  results = index.query([query_embedding], top_k=5, include_metadata=True)

  return results["matches"]


if __name__ == "__main__":
  main()