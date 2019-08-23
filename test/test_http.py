import json

from starlette.testclient import TestClient


def test_schema(default_schema):
    res = default_schema.execute(
        """
        query NumWithArg{
            aNum
            aNumWithArgs(num: 99)
        }
        """
    )
    assert res.data["aNum"] == 1
    assert res.data["aNumWithArgs"] == 99
    assert res.errors is None


def test_http_asig_json_body(default_application):
    request_body_data = {
        "query": """
        query NumWithArg{
            aNum
            aNumWithArgs(num: 99)
            getContext
        }
        """,
        "variables": {},
        "operation_name": None,
    }
    client = TestClient(default_application)
    resp = client.post("/", json=request_body_data, headers={"foo": "bar"})
    res = resp.json()
    assert resp.status_code == 200
    assert res.get("errors") is None
    assert res["data"]["aNum"] == 1
    assert res["data"]["aNumWithArgs"] == 99
    context = json.loads(res["data"]["getContext"])
    assert context['headers']["foo"] == "bar"
