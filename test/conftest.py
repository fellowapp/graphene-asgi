import asyncio
import graphene
import pytest
from graphene_asgi.application import Application


class Query(graphene.ObjectType):

    a_num = graphene.Int()
    a_num_with_args = graphene.Field(graphene.Int, required=True, num=graphene.Int(required=True))
    get_context = graphene.JSONString()

    def resolve_a_num(self, info):
        return 1

    def resolve_a_num_with_args(self, info, num):
        return num

    def resolve_get_context(self, info):
        return info.context


async def sub_count_seconds(root, info, up_to):
    for i in range(up_to):
        yield i
        await asyncio.sleep(1.0)
    yield up_to


class Subscription(graphene.ObjectType):
    count_seconds = graphene.Float(up_to=graphene.Float())

    async def resolve_count_seconds(root, info, up_to):
        for i in range(up_to):
            yield i
            await asyncio.sleep(1.0)
        yield up_to


schema = graphene.Schema(query=Query, subscription=Subscription)


@pytest.fixture
def default_schema():
    return schema

@pytest.fixture
def default_application(default_schema):
    return Application(default_schema)
