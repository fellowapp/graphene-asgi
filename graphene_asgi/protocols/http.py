import json

from .base import ProtocolBase


class HTTPHandler(ProtocolBase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.http_body = b""
        self.http_has_more_body = True
        self.http_received_body_length = 0

    async def run(self):
        body = await self.body
        query_string, variables, operation_name, _params = await self.app.parse_request(
            self.scope, body
        )
        context = await self.app.get_context(self.scope, body)
        res = await self.app.execute(
            source=query_string,
            context_value=context,
            variable_values=variables,
            operation_name=operation_name,
        )
        resp = json.dumps(res._asdict()).encode()
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(resp)).encode()),
        ]
        if not res.errors:
            await self.send(
                {"type": "http.response.start", "status": 200, "headers": headers}
            )
        else:
            await self.send(
                {"type": "http.response.start", "status": 400, "headers": headers}
            )
        await self.send(
            {"type": "http.response.body", "body": resp, "more_body": False}
        )

    @property
    async def body(self):
        return b"".join([chunks async for chunks in self._body_iter()])

    async def _body_iter(self, save=True):
        if self.http_received_body_length > 0 and self.http_has_more_body:
            raise RuntimeError("body iter is already started and is not finished")
        if self.http_received_body_length > 0 and not self.http_has_more_body:
            yield self.http_body
        content_lenth = None
        transfer_encoding = None
        for k, v in self.scope["headers"]:
            if k.decode("ascii").lower() == "content-length":
                content_lenth = int(v)
            elif k.decode("ascii").lower() == "transfer-encoding":
                transfer_encoding = v.decode("ascii")
        req_body_length = content_lenth if transfer_encoding != "chunked" else None
        while self.http_has_more_body:
            if req_body_length and self.http_received_body_length > req_body_length:
                raise RuntimeError("body is longer than declared")
            message = await self.receive()
            message_type = message.get("type")
            if message_type != "http.request":
                continue
            chunk = message.get("body", b"")
            if not isinstance(chunk, bytes):
                raise RuntimeError("Chunk is not bytes")
            if save:
                self.http_body += chunk
            self.http_has_more_body = message.get("more_body", False) or False
            self.http_received_body_length += len(chunk)
            yield chunk
