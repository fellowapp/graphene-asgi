import json

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
        self.futures = {}
        return super().__init__(scope, receive, send, app)

    async def handle_message(self, text=None):
        message = json.loads(text)
        type = message["type"]
        if type == GQL_CONNECTION_INIT:
            await self.on_connection_init(message.get("payload", {}))
        if type == GQL_START:
            await self.on_start(message["id"], message["payload"])

    async def on_start(self, id: str, payload: dict):
        context = await self.app.get_context(self.scope, payload)
        res = await self.app.execute(
            source=payload['query'],
            context_value=context,
            variable_values=payload['variables'],
        )
        print(res)
        # import ipdb; ipdb.set_trace()
        # res.subscribe(self.on_response, partialmethod(self.on_response, id))

    async def on_response(self, id: str, resp):
        print(id, resp)

    async def on_connection_init(self, payload: dict):
        return await self.send_graphql_ws_message(GQL_CONNECTION_ACK)

    async def send_graphql_ws_message(self, type, content=None):
        if content is None:
            content = {}
        return await self.send({
            "type": "websocket.send",
            "text": json.dumps({
                "type": type,
                **content,
            })
        })

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
                break
            if type == "websocket.receive":
                await self.handle_message(text=message.get("text"))
