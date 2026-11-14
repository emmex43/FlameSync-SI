import os
from pathlib import Path
import httpx
from openai import AsyncOpenAI
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# 1. Resolve paths to the vector DB we just built
BASE_DIR = Path(__file__).resolve().parents[3]
VECTOR_DB_DIR = BASE_DIR / "data" / "vector_db"

# 2. Initialize the local embedding model and load ChromaDB into memory
print("Loading ChromaDB and Embedding model into memory...")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vector_store = Chroma(persist_directory=str(
    VECTOR_DB_DIR), embedding_function=embeddings)

# 3. Initialize the official OpenRouter LLM client
# Ensure this is your real OpenRouter key
api_key = os.getenv("OPENROUTER_API_KEY")

custom_http_client = httpx.AsyncClient(
    headers={
        "User-Agent": "FlameSync/1.0",
        "HTTP-Referer": "http://localhost:8000",  # Required by OpenRouter free tier
        "X-Title": "FlameSync Space Apps"        # Required by OpenRouter free tier
    }
)

client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",  # Changed back to official URL
    api_key=api_key,
    http_client=custom_http_client
)


async def generate_rag_response(user_query: str) -> dict:
    """Searches the NASA PDFs and generates a cited response."""

    # Step A: Semantic Search - grab the top 3 most relevant chunks
    results = vector_store.similarity_search(user_query, k=3)

    # Step B: Format the retrieved text and track the source PDF filenames
    context = "\n\n---\n\n".join(
        [f"Excerpt {i+1}:\n{doc.page_content}" for i, doc in enumerate(results)])

    # Extract unique source filenames (stripping the full path for clean UI display)
    sources = list(
        set([Path(doc.metadata.get("source", "Unknown")).name for doc in results]))

    # Step C: Prompt the LLM using strict constraints
    system_prompt = f"""
    You are the FlameSync SI Research Assistant, an expert in microgravity fire safety.
    Answer the user's question using ONLY the provided context excerpts from NASA research papers.
    If the answer cannot be found in the excerpts, politely state that the information is not in the current database.
    Use Markdown for readability.
    
    NASA Context Excerpts:
    {context}
    """

    # Update the model ID in the chat completion call
    response = await client.chat.completions.create(
        model="nvidia/nemotron-3.5-super-vl:free",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ],
        temperature=0.2
    )

    return {
        "answer": response.choices[0].message.content,
        "sources": sources
    }
