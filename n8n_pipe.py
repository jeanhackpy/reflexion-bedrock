"""
title: n8n Pipe Function
author: Cole Medin
author_url: https://www.youtube.com/@ColeMedin
version: 0.2.0

This module defines a Pipe class that utilizes N8N for an Agent.
Refactored for async performance and industry standards.
"""

import time
import httpx
import logging
from typing import Optional, Callable, Awaitable, Any, Union
from pydantic import BaseModel, Field

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_event_info(event_emitter: Any) -> tuple[Optional[str], Optional[str]]:
    """
    Extracts chat_id and message_id from the event_emitter's closure.
    This is a bit of a hack specific to Open WebUI's internal structure.
    """
    if not event_emitter or not hasattr(event_emitter, "__closure__") or not event_emitter.__closure__:
        return None, None

    for cell in event_emitter.__closure__:
        if hasattr(cell, "cell_contents"):
            contents = cell.cell_contents
            if isinstance(contents, dict):
                chat_id = contents.get("chat_id")
                message_id = contents.get("message_id")
                if chat_id or message_id:
                    return chat_id, message_id
    return None, None

class Pipe:
    class Valves(BaseModel):
        n8n_url: str = Field(
            default="",
            description="The URL of your n8n webhook."
        )
        n8n_bearer_token: str = Field(
            default="",
            description="Bearer token for n8n authentication."
        )
        input_field: str = Field(
            default="chatInput",
            description="The field name n8n expects for the user input."
        )
        response_field: str = Field(
            default="output",
            description="The field name n8n returns the response in."
        )
        emit_interval: float = Field(
            default=2.0,
            description="Interval in seconds between status emissions."
        )
        enable_status_indicator: bool = Field(
            default=True,
            description="Enable or disable status indicator emissions."
        )

    def __init__(self):
        self.type = "pipe"
        self.id = "n8n_pipe"
        self.name = "N8N Pipe"
        self.valves = self.Valves()
        self.last_emit_time = 0

    async def emit_status(
        self,
        __event_emitter__: Optional[Callable[[dict], Awaitable[None]]],
        level: str,
        message: str,
        done: bool,
    ):
        current_time = time.time()
        if (
            __event_emitter__
            and self.valves.enable_status_indicator
            and (
                current_time - self.last_emit_time >= self.valves.emit_interval or done
            )
        ):
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "status": "complete" if done else "in_progress",
                        "level": level,
                        "description": message,
                        "done": done,
                    },
                }
            )
            self.last_emit_time = current_time

    async def pipe(
        self,
        body: dict,
        __user__: Optional[dict] = None,
        __event_emitter__: Optional[Callable[[dict], Awaitable[None]]] = None,
        __event_call__: Optional[Callable[[dict], Awaitable[dict]]] = None,
    ) -> Union[str, dict]:
        if not self.valves.n8n_url:
            return "Error: n8n_url is not configured in Valves."

        await self.emit_status(
            __event_emitter__, "info", "Calling N8N Workflow...", False
        )

        chat_id, _ = extract_event_info(__event_emitter__)
        messages = body.get("messages", [])

        if not messages:
            error_msg = "No messages found in the request body"
            await self.emit_status(__event_emitter__, "error", error_msg, True)
            return error_msg

        question = messages[-1]["content"]

        try:
            headers = {
                "Authorization": f"Bearer {self.valves.n8n_bearer_token}",
                "Content-Type": "application/json",
            }
            payload = {
                "sessionId": chat_id or "default_session",
                self.valves.input_field: question
            }

            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    self.valves.n8n_url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                result = response.json()

                # Check if result is a list (n8n often returns a list)
                if isinstance(result, list) and len(result) > 0:
                    result = result[0]

                n8n_response = result.get(self.valves.response_field, "No response from n8n.")

            # Append the response to messages to maintain history if needed by the UI
            # Some UIs expect the pipe to return the whole body, some just the string
            # In Open WebUI, returning the string replaces the assistant response
            body["messages"].append({"role": "assistant", "content": n8n_response})

        except httpx.HTTPStatusError as e:
            error_msg = f"HTTP Error {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            await self.emit_status(__event_emitter__, "error", error_msg, True)
            return error_msg
        except Exception as e:
            error_msg = f"Error during sequence execution: {str(e)}"
            logger.exception(error_msg)
            await self.emit_status(__event_emitter__, "error", error_msg, True)
            return error_msg

        await self.emit_status(__event_emitter__, "info", "Complete", True)
        return n8n_response
