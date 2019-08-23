import json
from typing import Any, Awaitable, Callable, Optional, Tuple, Union

from graphene import Schema

from .protocols import HTTPHandler, GraphqlWSHandler, WebsocketHandler


class Application:
    def __init__(self, schema: Schema):
        self.schema = schema

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
            data.pop("operation_name", None),
            data,
        )

    async def execute(self, **kwargs):
        default_kwargs = {}
        return await self.schema.execute_async(
            **default_kwargs, **kwargs,
        )

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


GRAPHIQL = GRAPHIQL = """
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
    <!--
      This GraphiQL example depends on Promise and fetch, which are available in
      modern browsers, but can be "polyfilled" for older browsers.
      GraphiQL itself depends on React DOM.
      If you do not want to rely on a CDN, you can host these files locally or
      include them directly in your favored resource bunder.
    -->
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
      /**
       * This GraphiQL example illustrates how to use some of GraphiQL's props
       * in order to enable reading and updating the URL parameters, making
       * link sharing of queries a little bit easier.
       *
       * This is only one example of this kind of feature, GraphiQL exposes
       * various React params to enable interesting integrations.
       */
      // Parse the search string to get url parameters.
      var search = window.location.search;
      var parameters = {};
      search.substr(1).split('&').forEach(function (entry) {
        var eq = entry.indexOf('=');
        if (eq >= 0) {
          parameters[decodeURIComponent(entry.slice(0, eq))] =
            decodeURIComponent(entry.slice(eq + 1));
        }
      });
      // if variables was provided, try to format it.
      if (parameters.variables) {
        try {
          parameters.variables =
            JSON.stringify(JSON.parse(parameters.variables), null, 2);
        } catch (e) {
          // Do nothing, we want to display the invalid JSON as a string, rather
          // than present an error.
        }
      }
      // When the query and variables string is edited, update the URL bar so
      // that it can be easily shared
      function onEditQuery(newQuery) {
        parameters.query = newQuery;
      }
      function onEditVariables(newVariables) {
        parameters.variables = newVariables;
      }
      function onEditOperationName(newOperationName) {
        parameters.operationName = newOperationName;
      }
      // Defines a GraphQL fetcher using the fetch API. You're not required to
      // use fetch, and could instead implement graphQLFetcher however you like,
      // as long as it returns a Promise or Observable.
      function graphQLFetcher(graphQLParams) {
        return fetch(window.location.pathname, {
          method: 'post',
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(graphQLParams),
          credentials: 'include',
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
      // subscription fetcher
      var subscriptionsClient = new window.SubscriptionsTransportWs.SubscriptionClient("ws://" + window.location.host + window.location.pathname, { reconnect: true });
      var subscriptionsFetcher = GraphiQLSubscriptionsFetcher.graphQLFetcher(subscriptionsClient, graphQLFetcher);
      // Render <GraphiQL /> into the body.
      // See the README in the top level of this module to learn more about
      // how you can customize GraphiQL by providing different values or
      // additional child elements.
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
"""
