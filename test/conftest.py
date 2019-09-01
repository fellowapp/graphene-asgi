import asyncio

import graphene
import pytest

from graphene_asgi import Application


class Query(graphene.ObjectType):

    a_num = graphene.Int()
    a_num_with_args = graphene.Field(
        graphene.Int, required=True, num=graphene.Int(required=True)
    )
    get_context = graphene.JSONString()

    def resolve_a_num(self, info):
        return 1

    def resolve_a_num_with_args(self, info, num):
        return num

    def resolve_get_context(self, info):
        return info.context


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


@pytest.fixture
def default_schema():
    return schema


@pytest.fixture
def default_application(default_schema):
    return Application(default_schema)
