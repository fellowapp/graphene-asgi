from graphene_asgi.application import Application
from .conftest import schema
application = Application(schema)