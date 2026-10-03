"""Intelligent search assistant with database tools (MOCKED FOR USER IMPLEMENTATION).

========================================================================================
GUIDE FOR USER IMPLEMENTATION:
========================================================================================
To implement the real LangChain Conversational Agent:
1. Define the LangChain tools using the `@tool` decorator:
   ```python
   from langchain_core.tools import tool

   @tool
   def search_catalog_tool(query: str, category: str = "movies") -> str:
       '''Search the local Linkschin database for media titles, releases, and qualities.'''
       items = db.search(category=category, query=query, limit=5)
       return json.dumps([asdict(i) for i in items])

   @tool
   def check_source_health_tool() -> str:
       '''Check real-time health and status of upstream media portal scrapers.'''
       records = db.get_all_source_health()
       return json.dumps(records)
   ```
2. Create the tool-calling agent:
   ```python
   from langchain_openai import ChatOpenAI
   from langchain.agents import create_tool_calling_agent, AgentExecutor
   from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

   llm = ChatOpenAI(
       api_key=os.environ.get("LLM_API_KEY"),
       model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
       streaming=True
   )
   tools = [search_catalog_tool, check_source_health_tool]
   prompt = ChatPromptTemplate.from_messages([
       ("system", "You are the Persian/English Linkschin AI search assistant..."),
       MessagesPlaceholder(variable_name="chat_history"),
       ("human", "{input}"),
       MessagesPlaceholder(variable_name="agent_scratchpad"),
   ])
   agent = create_tool_calling_agent(llm, tools, prompt)
   agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
   ```
3. In `generate_chat_events`, call `agent_executor.astream(...)` and yield SSE events.
========================================================================================
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict
import json
import logging
from typing import AsyncGenerator

import db
from models import Category

logger = logging.getLogger("web.chat")

# In-memory session history store
_SESSION_HISTORIES: dict[str, list[dict]] = {}


async def process_chat_message(
    message: str,
    session_id: str | None = None,
    category: str = "movies",
) -> dict:
    """Mock process chat message and return JSON response.

    # TODO: User implementation with LangChain agent_executor.ainvoke(...)
    """
    session = session_id or "default"
    logger.info("Mock processing chat message for session %s: %s", session, message)

    lower = message.lower()
    media_items = []

    if any(k in lower for k in ["source", "down", "منبع", "خراب", "سلامت", "health"]):
        sources = db.get_all_source_health()
        inactive = [s["source_id"] for s in sources if s.get("state") != "ok"]
        if inactive:
            reply = f"منابع زیر در حال حاضر با اختلال مواجه هستند: {', '.join(inactive)}. سایر منابع در دسترس هستند."
        else:
            reply = "تمامی منابع ثبت‌شده فعال و در دسترس می‌باشند."
    elif any(k in lower for k in ["دوبله", "dub", "1080", "کیفیت"]):
        items = db.search(category=category, query="", limit=3)
        media_items = [asdict(i) for i in items]
        reply = "نسخه‌های با کیفیت بالا و دوبله فارسی مطابق جستجوی شما یافت شدند:"
    else:
        items = db.search(category=category, query=message, limit=3)
        if items:
            media_items = [asdict(i) for i in items]
            reply = f"عناوین یافت‌شده برای «{message}»:"
        else:
            reply = f"پاسخ دستیار: پرسش شما درباره «{message}» بررسی شد. می‌توانید عنوان خاص یا کیفیت مورد نظر را بفرمایید."

    # Save to history
    _SESSION_HISTORIES.setdefault(session, []).append({"user": message, "bot": reply})

    return {
        "session_id": session,
        "message": reply,
        "media_items": media_items,
    }


async def generate_chat_events(
    message: str,
    session_id: str | None = None,
    category: str = "movies",
) -> AsyncGenerator[str, None]:
    """Yield Server-Sent Events (SSE) for streaming chat assistant."""
    session = session_id or "default"

    # Event 1: Status
    yield f"event: status\ndata: {json.dumps({'step': 'Searching media catalog...'})}\n\n"
    await asyncio.sleep(0.15)

    # Call processor (or LangChain agent)
    res = await process_chat_message(message, session, category)

    # Event 2: Delta text stream
    words = res["message"].split(" ")
    for word in words:
        yield f"event: delta\ndata: {json.dumps({'text': word + ' '})}\n\n"
        await asyncio.sleep(0.04)

    # Event 3: Media Cards if found
    for item in res.get("media_items", []):
        yield f"event: media_card\ndata: {json.dumps({'item': item})}\n\n"

    # Event 4: Done
    yield f"event: done\ndata: {json.dumps({'session_id': session})}\n\n"


def clear_session(session_id: str) -> None:
    _SESSION_HISTORIES.pop(session_id, None)
