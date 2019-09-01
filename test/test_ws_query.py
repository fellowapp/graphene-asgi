import json

from starlette.testclient import WebSocketTestSession


def test_query_through_ws(default_application):
    request_body_data = {
        "query": """
        query test($num: Int!){
            aNum
            aNumWithArgs(num: $num)
            getContext
        }
        """,
        "variables": {"num": 100},
        "operation_name": "test",
        "id": "foo",
    }
    with WebSocketTestSession(
        default_application,
        {"type": "websocket", "headers": [[b"foo", b"bar"]], "subprotocols": []},
    ) as session:
        session.send_text(json.dumps(request_body_data))
        res = session.receive_json()
        assert res.get("errors") is None
        assert res["id"] == "foo"
        assert res["data"]["aNum"] == 1
        assert res["data"]["aNumWithArgs"] == 100
        assert json.loads(res["data"]["getContext"])["headers"]["foo"] == "bar"
