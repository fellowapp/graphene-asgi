import json
from typing import Any, Awaitable, Callable, Optional, Tuple

from graphene import Schema
from graphql.execution.execute import ExecutionResult
from graphql.language import parse
from graphql.language.ast import OperationDefinitionNode, OperationType

from .protocols import GraphqlWSHandler, HTTPHandler, WebsocketHandler


class Application:
    def __init__(self, schema: Schema):
        self.schema = schema
        # hack to attach subscribe_{field_name} methods to fields in the schema
        for name in self.schema.subscription._meta.fields.keys():
            field = schema.graphql_schema.subscription_type.fields[
                schema.graphql_schema.get_name(name)
            ]
            field.subscribe = getattr(
                self.schema.subscription, "{}_{}".format("subscribe", name)
            )

    async def get_context(self, scope, message):
        return {
            **scope,
            "headers": {
                k.decode("ascii"): v.decode("ascii") for k, v in scope["headers"]
            },
            "query_string": scope.get("query_string", b"").decode(),
        }

    async def parse_request(
        self, scope, message
    ) -> Tuple[str, Optional[dict], Optional[str], dict]:
        data = json.loads(message)
        return (
            data.pop("query"),
            data.pop("variables", {}),
            data.pop("operationName", None),
            data,
        )

    def format_res(self, res: ExecutionResult):
        data = dict(res._asdict())
        if data["errors"]:
            data["errors"] = [e.formatted for e in data["errors"]]
        else:
            del data["errors"]
        return data

    async def execute(self, **kwargs):
        default_kwargs = {}
        assert "source" in kwargs
        document = parse(kwargs["source"])
        operation_defs = {
            d.name.value if d.name else None: d
            for d in document.definitions
            if isinstance(d, OperationDefinitionNode)
        }
        if len(operation_defs) == 1:
            op = next(o for o in operation_defs.values())
        # let it fail. Don't want to return error myself
        elif None in operation_defs:
            return await self.schema.execute_async(**default_kwargs, **kwargs)
        else:
            if (
                "operation_name" not in kwargs
                or kwargs["operation_name"] not in operation_defs
            ):
                # let it fail. Don't want to return error myself
                return await self.schema.execute_async(**default_kwargs, **kwargs)
            op = operation_defs[kwargs["operation_name"]]
        if op.operation == OperationType.SUBSCRIPTION:
            kwargs["document"] = document
            kwargs.pop("source")
            return await self.schema.subscribe(**default_kwargs, **kwargs)
        return await self.schema.execute_async(**default_kwargs, **kwargs)

    async def check_access(self, scope):
        return True

    async def __call__(
        self,
        scope: dict,
        receive: Callable[[Any], Awaitable],
        send: Callable[[Any], Awaitable],
    ):
        if scope["type"] == "http":
            if scope["method"].lower() == "get":
                resp_body = GRAPHIQL.encode()
                await send(
                    {
                        "type": "http.response.start",
                        "status": 200,
                        "headers": [(b"content-type", b"text/html")],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": resp_body,
                        "more_body": False,
                    }
                )
                return
            else:
                return await HTTPHandler(scope, receive, send, app=self).run()
        if scope["type"] == "websocket":
            if "graphql-ws" in scope["subprotocols"]:
                return await GraphqlWSHandler(scope, receive, send, app=self).run()
            return await WebsocketHandler(scope, receive, send, app=self).run()


GRAPHIQL = """
<!--
 *  Copyright (c) Facebook, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the license found in the
 *  LICENSE file in the root directory of this source tree.
-->
<!DOCTYPE html>
<html>
  <head>
    <style>
      body {
        height: 100%;
        margin: 0;
        width: 100%;
        overflow: hidden;
      }
      #graphiql {
        height: 100vh;
      }
    </style>
    <link href="//unpkg.com/graphiql@0.12.0/graphiql.css" rel="stylesheet"/>
    <script src="//unpkg.com/whatwg-fetch@2.0.3/fetch.js"></script>
    <script src="//unpkg.com/react@16.2.0/umd/react.production.min.js"></script>
    <script src="//unpkg.com/react-dom@16.2.0/umd/react-dom.production.min.js"></script>
    <script src="//unpkg.com/graphiql@0.12.0/graphiql.min.js"></script>
    <script src="//unpkg.com/subscriptions-transport-ws@0.8.3/browser/client.js"></script>
    <script src="//unpkg.com/graphiql-subscriptions-fetcher@0.0.2/browser/client.js"></script>
  </head>
  <body>
    <div id="graphiql">Loading...</div>
    <script>
      var parameters = {};
      function onEditQuery(newQuery) {
        parameters.query = newQuery;
      }
      function onEditVariables(newVariables) {
        parameters.variables = newVariables;
      }
      function onEditOperationName(newOperationName) {
        parameters.operationName = newOperationName;
      }
      function graphQLFetcher(graphQLParams) {
        return fetch(window.location.pathname, {
          method: 'post',
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(graphQLParams),
        }).then(function (response) {
          return response.text();
        }).then(function (responseBody) {
          try {
            return JSON.parse(responseBody);
          } catch (error) {
            return responseBody;
          }
        });
      }
      var subscriptionsClient = new window.SubscriptionsTransportWs.SubscriptionClient("ws://" + window.location.host + window.location.pathname, { reconnect: true });
      var subscriptionsFetcher = GraphiQLSubscriptionsFetcher.graphQLFetcher(subscriptionsClient, graphQLFetcher);
      ReactDOM.render(
        React.createElement(GraphiQL, {
          fetcher: subscriptionsFetcher,
          query: parameters.query,
          variables: parameters.variables,
          operationName: parameters.operationName,
          onEditQuery: onEditQuery,
          onEditVariables: onEditVariables,
          onEditOperationName: onEditOperationName
        }),
        document.getElementById('graphiql')
      );
    </script>
  </body>
</html>
"""  # noqa
