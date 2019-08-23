import asyncio
import json
from typing import AsyncIterator

from graphql.execution.execute import ExecutionResult

from .base import ProtocolBase

GQL_CONNECTION_INIT = "connection_init"
GQL_CONNECTION_ACK = "connection_ack"
GQL_CONNECTION_ERROR = "connection_error"
GQL_CONNECTION_KEEP_ALIVE = "ka"
GQL_CONNECTION_TERMINATE = "connection_terminate"
GQL_START = "start"
GQL_DATA = "data"
GQL_ERROR = "error"
GQL_COMPLETE = "complete"
GQL_STOP = "stop"


class GraphqlWSHandler(ProtocolBase):
    def __init__(self, scope, receive, send, app):
        self.subscriptions = {}
        super().__init__(scope, receive, send, app)

    async def handle_message(self, text=None):
        message = json.loads(text)
        type = message["type"]
        if type == GQL_CONNECTION_INIT:
            await self.on_connect(message.get("payload", {}))
        if type == GQL_START:
            await self.on_operation(message["id"], message["payload"])
        if type == GQL_STOP:
            await self.on_stop(message["id"])
        if type == GQL_CONNECTION_TERMINATE:
            await self.send({"type": "websocket.close"})

    async def on_operation(self, id: str, payload: dict):
        context = await self.app.get_context(self.scope, payload)
        res = await self.app.execute(
            source=payload["query"],
            context_value=context,
            variable_values=payload["variables"],
        )
        if isinstance(res, AsyncIterator):
            self.subscriptions[id] = asyncio.ensure_future(
                self._consume_stream(res, id)
            )
        elif isinstance(res, ExecutionResult):
            if res.errors:
                await self.send_graphql_ws_message(
                    GQL_ERROR,
                    {"payload": [{"message": e.message} for e in res.errors], "id": id},
                )
            else:
                await self.send_graphql_ws_message(
                    GQL_DATA, {"payload": self.app.format_res(res), "id": id}
                )

    async def on_connect(self, payload: dict):
        return await self.send_graphql_ws_message(GQL_CONNECTION_ACK)

    async def on_stop(self, id):
        fut = self.subscriptions.pop(id, None)
        if fut:
            fut.cancel()

    async def send_graphql_ws_message(self, type, content=None):
        if content is None:
            content = {}
        return await self.send(
            {"type": "websocket.send", "text": json.dumps({"type": type, **content})}
        )

    async def run(self):
        assert "graphql-ws" in self.scope["subprotocols"]
        message = await self.receive()
        assert message["type"] == "websocket.connect"
        if await self.app.check_access(self.scope):
            await self.send({"type": "websocket.accept", "subprotocol": "graphql-ws"})
        else:
            await self.send({"type": "websocket.close"})
        while True:
            message = await self.receive()
            type = message["type"]
            if type == "websocket.disconnect":
                for fut in self.subscriptions.values():
                    fut.cancel()
                break
            if type == "websocket.receive":
                await self.handle_message(text=message.get("text"))

    async def _consume_stream(self, stream, id):
        async for item in stream:
            try:
                await self.send_graphql_ws_message(
                    GQL_DATA, {"payload": self.app.format_res(item), "id": id}
                )
            except asyncio.CancelledError:
                break
        else:
            await self.send_graphql_ws_message(GQL_COMPLETE, {"id": id})
