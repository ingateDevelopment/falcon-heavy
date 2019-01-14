from __future__ import unicode_literals, print_function

import unittest

from falcon_heavy.schema.exceptions import SchemaError
from falcon_heavy.schema.types import Object
from falcon_heavy.openapi import (
    Info,
    Contact,
    License,
    Server,
    Components,
    Operation,
    PathItem,
    ExternalDocumentation,
    HeaderParameter,
    QueryParameter,
    PathParameter,
    RequestBody,
    MediaType,
    Response,
    Tag,
    Schema
)


class SchemaTest(unittest.TestCase):

    def _validate_data(self, data, schema):
        try:
            Object.from_raw(schema, data)
        except SchemaError as e:
            self.fail(str(e))

    def _must_failed(self, data, schema, errors=None):
        try:
            Object.from_raw(schema, data)
        except SchemaError as e:
            self.assertEqual(e.errors, errors)
        else:
            self.fail()

    def test_info(self):
        data = {
            "title": "Sample Pet Store App",
            "description": "This is a sample server for a pet store.",
            "termsOfService": "http://example.com/terms/",
            "contact": {
                "name": "API Support",
                "url": "http://www.example.com/support",
                "email": "support@example.com"
            },
            "license": {
                "name": "Apache 2.0",
                "url": "https://www.apache.org/licenses/LICENSE-2.0.html"
            },
            "version": "1.0.1"
        }
        self._validate_data(data, Info)

    def test_contact(self):
        data = {
            "name": "API Support",
            "url": "http://www.example.com/support",
            "email": "support@example.com"
        }
        self._validate_data(data, Contact)

    def test_license(self):
        data = {
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0.html"
        }
        self._validate_data(data, License)

    def test_server(self):
        data = {
            "url": "https://{username}.gigantic-server.com:{port}/{basePath}",
            "description": "The production API server",
            "variables": {
                "username": {
                    "default": "demo",
                    "description": ("this value is assigned by the service provider, "
                                    "in this example `gigantic-server.com`")
                },
                "port": {
                    "enum": [
                        "8443",
                        "443"
                    ],
                    "default": "8443"
                },
                "basePath": {
                    "default": "v2"
                }
            }
        }
        self._validate_data(data, Server)

    def test_components(self):
        data = {
            "schemas": {
                "GeneralError": {
                    "type": "string"
                },
                "Category": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "format": "int64"
                        },
                        "name": {
                            "type": "string"
                        }
                    }
                },
                "Tag": {
                    "type": "object",
                    "properties": {
                        "id": {
                            "type": "integer",
                            "format": "int64"
                        },
                        "name": {
                            "type": "string"
                        }
                    }
                }
            },
            "parameters": {
                "skipParam": {
                    "name": "skip",
                    "in": "query",
                    "description": "number of items to skip",
                    "required": True,
                    "schema": {
                        "type": "integer",
                        "format": "int32"
                    }
                },
                "limitParam": {
                    "name": "limit",
                    "in": "query",
                    "description": "max records to return",
                    "required": True,
                    "schema": {
                        "type": "integer",
                        "format": "int32"
                    }
                }
            },
            "responses": {
                "NotFound": {
                    "description": "Entity not found."
                },
                "IllegalInput": {
                    "description": "Illegal input for operation."
                },
                "GeneralError": {
                    "description": "General Error",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/schemas/GeneralError"
                            }
                        }
                    }
                }
            },
            "securitySchemes": {
                "api_key": {
                    "type": "apiKey",
                    "name": "api_key",
                    "in": "header"
                },
                "petstore_auth": {
                    "type": "oauth2",
                    "flows": {
                        "implicit": {
                            "authorizationUrl": "http://example.org/api/oauth/dialog",
                            "scopes": {
                                "write:pets": "modify pets in your account",
                                "read:pets": "read your pets"
                            },
                            "tokenUrl": "https://"
                        }
                    }
                }
            }
        }
        self._validate_data(data, Components)

    def test_path_item(self):
        data = {
            "x-schemas": {
                "Pet": {
                    "type": "string"
                }
            },
            "x-resource": "controllers.Pets",
            "get": {
                "description": "Returns all pets from the system that the user has access to",
                "responses": {
                    "200": {
                        "description": "A list of pets.",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {
                                        "$ref": "#/x-schemas/Pet"
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        self._validate_data(data, PathItem)

    def test_operation(self):
        data = {
            "tags": [
                "pet"
            ],
            "summary": "Updates a pet in the store with form data",
            "operationId": "updatePetWithForm",
            "parameters": [
                {
                    "name": "petId",
                    "in": "path",
                    "description": "ID of pet that needs to be updated",
                    "required": True,
                    "schema": {
                        "type": "string"
                    }
                }
            ],
            "requestBody": {
                "content": {
                    "application/x-www-form-urlencoded": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "description": "Updated name of the pet",
                                    "type": "string"
                                },
                                "status": {
                                    "description": "Updated status of the pet",
                                    "type": "string"
                                }
                            },
                            "required": [
                                "status"
                            ]
                        }
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "Pet updated.",
                    "content": {
                        "application/json": {},
                        "application/xml": {}
                    }
                },
                "405": {
                    "description": "Invalid input",
                    "content": {
                        "application/json": {},
                        "application/xml": {}
                    }
                }
            },
            "security": [
                {
                    "petstore_auth": [
                        "write:pets",
                        "read:pets"
                    ]
                }
            ]
        }
        self._validate_data(data, Operation)

    def test_external_documentation(self):
        data = {
            "description": "Find more info here",
            "url": "https://example.com"
        }
        self._validate_data(data, ExternalDocumentation)

    def test_parameter(self):
        # A header parameter with an array of 64 bit integer numbers
        data = {
            "name": "token",
            "in": "header",
            "description": "token to be passed as a header",
            "required": True,
            "schema": {
                "type": "array",
                "items": {
                    "type": "integer",
                    "format": "int64"
                }
            },
            "style": "simple",
            "x-property": "property"
        }
        self._validate_data(data, HeaderParameter)

        # A path parameter of a string value
        data = {
            "name": "username",
            "in": "path",
            "description": "username to fetch",
            "required": True,
            "schema": {
                "type": "string"
            }
        }
        self._validate_data(data, PathParameter)

        # An optional query parameter of a string value, allowing multiple values by repeating the query parameter
        data = {
            "name": "id",
            "in": "query",
            "description": "ID of the object to fetch",
            "required": False,
            "schema": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "style": "form",
            "explode": True
        }
        self._validate_data(data, QueryParameter)

        # A free-form query parameter, allowing undefined parameters of a specific type
        data = {
            "in": "query",
            "name": "freeForm",
            "schema": {
                "type": "object",
                "additionalProperties": {
                    "type": "integer"
                },
            },
            "style": "form"
        }
        self._validate_data(data, QueryParameter)

        # A complex parameter using content to define serialization
        data = {
            "in": "query",
            "name": "coordinates",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": [
                            "lat",
                            "long"
                        ],
                        "properties": {
                            "lat": {
                                "type": "number"
                            },
                            "long": {
                                "type": "number"
                            }
                        }
                    }
                }
            }
        }
        self._validate_data(data, QueryParameter)

    def test_request_body(self):
        data = {
            "x-schemas": {
                "User": {
                    "type": "string"
                }
            },
            "description": "user to add to the system",
            "content": {
                "application/json": {
                    "schema": {
                        "$ref": "#/x-schemas/User"
                    },
                    "examples": {
                        "user": {
                            "summary": "User Example",
                            "externalValue": "http://foo.bar/examples/user-example.json"
                        }
                    }
                },
                "application/xml": {
                    "schema": {
                        "$ref": "#/x-schemas/User"
                    },
                    "examples": {
                        "user": {
                            "summary": "User example in XML",
                            "externalValue": "http://foo.bar/examples/user-example.xml"
                        }
                    }
                },
                "text/plain": {
                    "examples": {
                        "user": {
                            "summary": "User example in Plain text",
                            "externalValue": "http://foo.bar/examples/user-example.txt"
                        }
                    }
                },
                "*/*": {
                    "examples": {
                        "user": {
                            "summary": "User example in other format",
                            "externalValue": "http://foo.bar/examples/user-example.whatever"
                        }
                    }
                }
            }
        }
        self._validate_data(data, RequestBody)

    def test_media_type(self):
        data = {
            "x-schemas": {
                "Pet": {
                    "type": "string"
                }
            },
            "x-examples": {
                "frog-example": {
                    "value": "example"
                }
            },
            "schema": {
                "$ref": "#/x-schemas/Pet"
            },
            "examples": {
                "cat": {
                    "summary": "An example of a cat",
                    "value": {
                        "name": "Fluffy",
                        "petType": "Cat",
                        "color": "White",
                        "gender": "male",
                        "breed": "Persian"
                    }
                },
                "dog": {
                    "summary": "An example of a dog with a cat's name",
                    "value": {
                        "name": "Puma",
                        "petType": "Dog",
                        "color": "Black",
                        "gender": "Female",
                        "breed": "Mixed"
                    },
                },
                "frog": {
                    "$ref": "#/x-examples/frog-example"
                }
            }
        }
        self._validate_data(data, MediaType)

    def test_response(self):
        # Response of an array of a complex type
        data = {
            "x-schemas": {
                "VeryComplexType": {
                    "type": "string"
                }
            },
            "description": "A complex object array response",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "array",
                        "items": {
                            "$ref": "#/x-schemas/VeryComplexType"
                        }
                    }
                }
            }
        }
        self._validate_data(data, Response)

        # Response with a string type
        data = {
            "description": "A simple string response",
            "content": {
                "text/plain": {
                    "schema": {
                        "type": "string"
                    }
                }
            }
        }
        self._validate_data(data, Response)

        # Plain text response with headers
        data = {
            "description": "A simple string response",
            "content": {
                "text/plain": {
                    "schema": {
                        "type": "string"
                    }
                }
            },
            "headers": {
                "X-Rate-Limit-Limit": {
                    "description": "The number of allowed requests in the current period",
                    "schema": {
                        "type": "integer"
                    }
                },
                "X-Rate-Limit-Remaining": {
                    "description": "The number of remaining requests in the current period",
                    "schema": {
                        "type": "integer"
                    }
                },
                "X-Rate-Limit-Reset": {
                    "description": "The number of seconds left in the current period",
                    "schema": {
                        "type": "integer"
                    }
                }
            }
        }
        self._validate_data(data, Response)

        # Response with no return value
        data = {
            "description": "object created"
        }
        self._validate_data(data, Response)

    def test_tag(self):
        data = {
            "name": "pet",
            "description": "Pets operations"
        }
        self._validate_data(data, Tag)

    def test_schema(self):
        # Simple Model
        data = {
            "x-schemas": {
                "Address": {
                    "type": "string"
                }
            },
            "type": "object",
            "required": [
                "name"
            ],
            "properties": {
                "name": {
                    "type": "string"
                },
                "address": {
                    "$ref": "#/x-schemas/Address"
                },
                "age": {
                    "type": "integer",
                    "format": "int32",
                    "minimum": 0
                }
            }
        }
        self._validate_data(data, Schema)

        # For a simple string to string mapping
        data = {
            "type": "object",
            "additionalProperties": {
                "type": "string"
            }
        }
        self._validate_data(data, Schema)

        # For a string to model mapping
        data = {
            "x-schemas": {
                "ComplexModel": {
                    "type": "string"
                }
            },
            "type": "object",
            "additionalProperties": {
                "$ref": "#/x-schemas/ComplexModel"
            }
        }
        self._validate_data(data, Schema)

        # Model with Example
        data = {
            "type": "object",
            "properties": {
                "id": {
                    "type": "integer",
                    "format": "int64"
                },
                "name": {
                    "type": "string"
                }
            },
            "required": [
                "name"
            ],
            "example": {
                "name": "Puma",
                "id": 1
            }
        }
        self._validate_data(data, Schema)

        # Models with Composition
        data = {
            "schemas": {
                "ErrorModel": {
                    "type": "object",
                    "required": [
                        "message",
                        "code"
                    ],
                    "properties": {
                        "message": {
                            "type": "string"
                        },
                        "code": {
                            "type": "integer",
                            "minimum": 100,
                            "maximum": 600
                        }
                    }
                },
                "ExtendedErrorModel": {
                    "allOf": [
                        {
                            "$ref": "#/schemas/ErrorModel"
                        },
                        {
                            "type": "object",
                            "required": [
                                "rootCause"
                            ],
                            "properties": {
                                "rootCause": {
                                    "type": "string"
                                }
                            }
                        }
                    ]
                }
            }
        }
        self._validate_data(data, Components)

        # Models with Polymorphism Support
        data = {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "discriminator": {
                        "propertyName": "petType"
                    },
                    "properties": {
                        "name": {
                            "type": "string"
                        },
                        "petType": {
                            "type": "string"
                        },
                        "pet": {
                            "$ref": "#/schemas/Pet"
                        }
                    },
                    "required": [
                        "name",
                        "petType"
                    ]
                },
                "Cat": {
                    "description": "A representation of a cat. "
                                   "Note that `Cat` will be used as the discriminator value.",
                    "allOf": [
                        {
                            "$ref": "#/schemas/Pet"
                        },
                        {
                            "type": "object",
                            "properties": {
                                "huntingSkill": {
                                    "type": "string",
                                    "description": "The measured skill for hunting",
                                    "default": "lazy",
                                    "enum": [
                                        "clueless",
                                        "lazy",
                                        "adventurous",
                                        "aggressive"
                                    ]
                                }
                            },
                            "required": [
                                "huntingSkill"
                            ]
                        }
                    ]
                },
                "Dog": {
                    "description": "A representation of a dog. "
                                   "Note that `Dog` will be used as the discriminator value.",
                    "allOf": [
                        {
                            "$ref": "#/schemas/Pet"
                        },
                        {
                            "type": "object",
                            "properties": {
                                "packSize": {
                                    "type": "integer",
                                    "format": "int32",
                                    "description": "the size of the pack the dog is from",
                                    "default": 0,
                                    "minimum": 0
                                }
                            },
                            "required": [
                                "packSize"
                            ]
                        }
                    ]
                }
            }
        }
        self._validate_data(data, Components)

    def test_discriminator(self):
        data = {
            "discriminator": {
                "propertyName": "petType"
            },
            "properties": {
                "petType": {
                    "type": "string"
                }
            },
            "required": [
                "petType"
            ]
        }
        self._validate_data(data, Schema)

        data = {
            "discriminator": {
                "propertyName": "petType"
            },
            "allOf": [
                {
                    "type": "object"
                }
            ]
        }
        self._must_failed(
            data,
            Schema,
            {'discriminator': ['The discriminator can only be used with the keywords `anyOf` or `oneOf`']}
        )

        data = {
            "discriminator": {
                "propertyName": "petType"
            },
            "oneOf": [
                {
                    "properties": {
                        "petType": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "petType"
                    ]
                }
            ]
        }
        self._validate_data(data, Schema)

        data = {
            "schemas": {
                "Pet": {
                    "type": "object",
                    "discriminator": {
                        "propertyName": "petType",
                        "mapping": {
                            "bee": "#/schemas/Bee"
                        }
                    }
                },
                "Bee": {
                    "type": "object"
                }
            }
        }

        self._must_failed(
            data,
            Components,
            {
                'schemas': {
                    'Pet': {
                        'discriminator': [
                            'The schema `#/schemas/Bee` is specified in discriminator mapping but'
                            ' not inherit the super schema `#/schemas/Pet`'
                        ]
                    }
                }
            }
        )

    def test_recursive_dependencies(self):
        data = {
            "schemas": {
                "Pet": {
                    "allOf": [
                        {
                            '$ref': '#/schemas/Pet'
                        }
                    ]
                }
            }
        }
        self._must_failed(
            data,
            Components,
            {'schemas': {u'Pet': {'allOf': [u'Has recursive dependency']}}}
        )

        data = {
            "schemas": {
                "Pet": {
                    "allOf": [
                        {
                            '$ref': '#/schemas/NewPet'
                        }
                    ]
                },
                "NewPet": {
                    "type": "object",
                    "properties": {
                        "pet": {
                            "$ref": "#/schemas/NewPet"
                        }
                    }
                }
            }
        }
        self._validate_data(data, Components)

    def test_unresolvable_recursive_reference(self):
        data = {
            "schemas": {
                "Pet": {
                    "$ref": "#/schemas/Bee"
                },
                "Bee": {
                    "$ref": "#/schemas/Pet"
                }
            }
        }

        self._must_failed(
            data,
            Components,
            {'schemas': {'Pet': ['Unresolvable recursive reference #/schemas/Bee'],
                         'Bee': ['Unresolvable recursive reference #/schemas/Pet']}}
        )

        data = {
            "schemas": {
                "Pet": {
                    "$ref": "#/schemas/Pet"
                }
            }
        }

        self._must_failed(
            data,
            Components,
            {'schemas': {'Pet': ['Unresolvable recursive reference #/schemas/Pet']}}
        )


if __name__ == '__main__':
    unittest.main()
