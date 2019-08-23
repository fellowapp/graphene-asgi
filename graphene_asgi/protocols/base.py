from typing import Any, Awaitable, Callable
class ProtocolBase:
    def __init__(
        self,
        scope: dict,
        receive: Callable[[Any], Awaitable],
        send: Callable[[Any], Awaitable],
        app: "graphene_asgi.application.Application",
    ):
        self.scope = scope
        self.receive = receive
        self.send = send
        self.app = app