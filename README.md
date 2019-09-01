# graphene-asgi

Graphene-asgi turns graphene schemas into asgi applications.

The created asgi application supports access through HTTP, WebScoket and [graphql-ws](https://github.com/apollographql/subscriptions-transport-ws/blob/master/PROTOCOL.md). (Graphql-ws is a websocket subprotocol that's assumed in most graphql subscription clients/servers.)

This project is experimental and depends on some packages in prerelease phase, including two core dependencies: `graphql-core-next` and `graphene`. These packages may have instable or incomplete APIs. Expect APIs of this project to change when upstream updates.

# Usage

Create schema:
```python3
# app.py
import graphene


class Query(graphene.ObjectType):

    a_num = graphene.Int()

    def resolve_a_num(self, info):
        return 1


class Subscription(graphene.ObjectType):
    count = graphene.Float(up_to=graphene.Float())

    async def resolve_count(self, info, up_to):
        return self

    async def subscribe_count(self, info, up_to):
        for i in range(int(up_to)):
            yield float(i)
            await asyncio.sleep(0.01)
        else:
            yield float(up_to)


schema = graphene.Schema(query=Query, subscription=Subscription)
```
Note that for a given field in a subcription type, there would be a subscription funtion as well as a resolve funtion. The `self` in resolve function will be the value that's yielded from subscribe function.

The name of subscription function must follow `subscribe_{filed_name}` and should return an async generator.

Create an asgi application:
```python3
# app.py
...
from graphene_asgi import Application
application = Application(schema, graphiql=True)
```

You can run this application directly with asgi servers (eg: `uvicorn app:application`) or plug it into other asgi applications. Graphiql is enabled by default


_An example server with a sample schema is included in test/server.py. To run it using uvicorn: ```uvicorn test.server:application --debug```_
