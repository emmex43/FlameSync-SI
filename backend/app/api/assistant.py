import logging
import os
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from openai import AsyncOpenAI
from pydantic import BaseModel

router = APIRouter(tags=["Assistant"])
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_DIR = PROJECT_ROOT / "data" / "vector_db"
load_dotenv(PROJECT_ROOT / ".env")

try:
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vector_store = Chroma(
        persist_directory=str(DB_DIR),
        embedding_function=embeddings,
    )
    document_count = vector_store._collection.count()
    if document_count == 0:
        raise RuntimeError(f"Chroma vector database at {DB_DIR} contains no documents")
    logger.info("Connected to %s with %d indexed document chunks", DB_DIR, document_count)
except Exception:
    logger.exception("Could not initialize RAG vector database at %s", DB_DIR)
    vector_store = None

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
client = (
    AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
    if OPENROUTER_API_KEY
    else None
)


class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[str]


def _display_source(source: str) -> str:
    if urlparse(source).scheme in {"http", "https"}:
        return source
    return Path(source).name or source


@router.post("/api/assistant/chat", response_model=ChatResponse)
async def chat_with_assistant(payload: ChatRequest):
    if vector_store is None:
        raise HTTPException(
            status_code=503,
            detail=f"RAG vector database is unavailable at {DB_DIR}. Check backend logs.",
        )
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="Assistant model is unavailable. Configure OPENROUTER_API_KEY in the project .env file.",
        )

    try:
        results = vector_store.similarity_search(payload.query, k=3)

        if results:
            context = "\n\n".join(document.page_content for document in results)
            sources = sorted(
                {
                    _display_source(document.metadata.get("source", "Unknown"))
                    for document in results
                }
            )
        else:
            context = "No relevant context found in the FlameSync database."
            sources = []

        system_prompt = (
            "You are the FlameSync AI Assistant, an expert in microgravity combustion and space safety. "
            "Use ONLY the provided context to answer the user's question. If the answer is not in the context, "
            "state that you do not have enough information. Do not hallucinate. Format with clear markdown."
        )
        user_prompt = f"Context from NASA Database:\n{context}\n\nQuestion:\n{payload.query}"

        response = await client.chat.completions.create(
            model="nvidia/nemotron-3.5-super-vl:free",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        answer = response.choices[0].message.content
        if answer is None:
            raise RuntimeError("Assistant model returned an empty response")
        return ChatResponse(answer=answer, sources=sources)

    except Exception as error:
        logger.exception("Assistant RAG request failed")
        raise HTTPException(
            status_code=502,
            detail="Assistant request failed. Check backend logs.",
        ) from error
