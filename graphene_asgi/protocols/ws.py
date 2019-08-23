import json

from .base import ProtocolBase


class WebsocketHandler(ProtocolBase):
    async def handle_message(self, bytes=None, text=None):
        if bytes is None and text is None:
            return
        if bytes is not None and text is not None:
            return
        message = text if text else bytes
        query_string, variables, operation_name, params = await self.app.parse_request(
            self.scope, message
        )
        context = await self.app.get_context(self.scope, message)
        res = await self.app.execute(
            source=query_string,
            context_value=context,
            variable_values=variables,
            operation_name=operation_name,
        )
        reply = json.dumps({**res._asdict(), "id": params.pop("id", None)})
        await self.send({"type": "websocket.send", "text": reply})

    async def run(self):
        message = await self.receive()
        assert message["type"] == "websocket.connect"
        if await self.app.check_access(self.scope):
            await self.send({"type": "websocket.accept"})
        else:
            await self.send({"type": "websocket.close"})
        while True:
            message = await self.receive()
            type = message["type"]
            if type == "websocket.disconnect":
                break
            if type == "websocket.receive":
                await self.handle_message(
                    bytes=message.get("bytes"), text=message.get("text")
                )
