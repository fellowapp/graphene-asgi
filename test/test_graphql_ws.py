from starlette.testclient import WebSocketTestSession


def test_query_through_ws(default_application):
    with WebSocketTestSession(
        default_application,
        {
            "type": "websocket",
            "headers": [[b"foo", b"bar"]],
            "subprotocols": ["graphql-ws"],
        },
    ) as session:
        session.send_text(r'{"type":"connection_init","payload":{}}')
        msg = session.receive_json()
        assert msg["type"] == "connection_ack"
        session.send_text(
            r'{"id":"1","type":"start","payload":{"query":"subscription {\n  count(upTo: 100)\n}","variables":null}}'  # noqa
        )
        for i in range(5):
            msg = session.receive_json()
            assert msg["type"] == "data"
            assert msg["id"] == "1"
            assert msg["payload"]["data"]["count"] == float(i)
        session.send_text(r'{"id":"1","type":"stop"}')
        session.send_text(
            r'{"id":"2","type":"start","payload":{"query":"subscription {\n  count(upTo: 3)\n}","variables":null}}'  # noqa
        )
        # Task.cancel() is not guaranteed.
        # might still receive some data from "1"
        id2_messages = []
        while len(id2_messages) < 5:
            msg = session.receive_json()
            if msg["id"] == "2":
                id2_messages.append(msg)
        for i, msg in enumerate(id2_messages[:-1]):
            assert msg["payload"]["data"]["count"] == float(i)
        assert id2_messages[-1]["type"] == "complete"
