from graphene_asgi import Application

from .conftest import schema

application = Application(schema)
