import os

from falcon_heavy.api import FalconHeavyApi, RuntimeResourceResolver


application = FalconHeavyApi(
    path=os.path.join(os.path.dirname(__file__), 'schema/petstore.yaml'),
    resource_resolver=RuntimeResourceResolver(package='tests.petstore'),
)
