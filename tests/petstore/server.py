import os

from hic_falcon_heavy.api import FalconHeavyApi
from hic_falcon_heavy.resource_resolver import RuntimeResourceResolver


application = FalconHeavyApi(
    specification_path=os.path.join(os.path.dirname(__file__), 'schema/petstore.yaml'),
    resource_resolver=RuntimeResourceResolver(package='tests.petstore'),
)
