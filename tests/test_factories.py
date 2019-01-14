from __future__ import absolute_import, unicode_literals

import datetime

import rfc3339

import unittest

from falcon_heavy.openapi import Schema, Components
from falcon_heavy.openapi.factories import PropertyFactory
from falcon_heavy.openapi import factories

from falcon_heavy.schema.types import Object, Context
from falcon_heavy.schema.cursor import Cursor
from falcon_heavy.schema.exceptions import SchemaError


class FactoriesTest(unittest.TestCase):

    def test_generate_oneOf(self):
        spec = {
            'x-schemas': {
                'Cat': {
                    'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        'name': {
                            'type': 'string'
                        }
                    }
                },
                'Dog': {
                    'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        'nickname': {
                            'type': 'string'
                        }
                    }
                }
            },
            'type': 'object',
            'properties': {
                'pet': {
                    'oneOf': [
                        {
                            '$ref': '#/x-schemas/Cat'
                        },
                        {
                            '$ref': '#/x-schemas/Dog'
                        }
                    ]
                }
            }
        }

        schema = Object.from_raw(Schema, spec)
        prop = PropertyFactory.generate(schema)

        cat_payload = {
            'pet': {
                'name': 'Misty'
            }
        }

        cat = prop.unmarshal(Cursor.from_raw(cat_payload))
        self.assertEqual(cat['pet']['name'], 'Misty')

        dog_payload = {
            'pet': {
                'nickname': 'Max'
            }
        }

        dog = prop.unmarshal(Cursor.from_raw(dog_payload))
        self.assertEqual(dog['pet']['nickname'], 'Max')

        # Implicit discriminator
        spec = {
            'schemas': {
                'Cat': {
                    'type': 'object',
                    'required': [
                        'pet_type'
                    ],
                    'properties': {
                        'pet_type': {
                            'type': 'string'
                        },
                        'name': {
                            'type': 'string'
                        }
                    }
                },
                'Dog': {
                    'type': 'object',
                    'additionalProperties': False,
                    'required': [
                        'pet_type'
                    ],
                    'properties': {
                        'pet_type': {
                            'type': 'string'
                        },
                        'nickname': {
                            'type': 'string'
                        }
                    }
                },
                'Pet': {
                    'type': 'object',
                    'properties': {
                        'pet': {
                            'oneOf': [
                                {
                                    '$ref': '#/schemas/Cat'
                                },
                                {
                                    '$ref': '#/schemas/Dog'
                                }
                            ],
                            'discriminator': {
                                'propertyName': 'pet_type'
                            }
                        }
                    }
                }
            }
        }

        schema = Object.from_raw(Components, spec)
        prop = PropertyFactory.generate(schema['schemas']['Pet'])

        cat_payload = {
            'pet': {
                'pet_type': 'Cat',
                'name': 'Misty'
            }
        }

        cat = prop.unmarshal(Cursor.from_raw(cat_payload))
        self.assertEqual(cat['pet']['name'], 'Misty')
        self.assertEqual(cat['pet']['pet_type'], 'Cat')

        ambiguous_cat_payload = {
            'pet': {
                'pet_type': '',
                'name': 'Misty'
            }
        }

        try:
            prop.unmarshal(Cursor.from_raw(ambiguous_cat_payload))
        except SchemaError as e:
            self.assertTrue("No one of property types are not matched to discriminator value" in str(e))
        else:
            self.fail("MUST failed because pet type not specified")

        dog_with_cat_properties = {
            'pet': {
                'pet_type': 'Dog',
                'name': 'Misty'
            }
        }

        try:
            prop.unmarshal(Cursor.from_raw(dog_with_cat_properties))
        except SchemaError as e:
            self.assertTrue("Unexpected additional property" in str(e))
        else:
            self.fail("MUST failed because Dog not accept additional properties")

        # Semi explicit discriminator
        spec = {
            'schemas': {
                'Cat': {
                    'type': 'object',
                    'additionalProperties': False,
                    'required': [
                        'pet_type'
                    ],
                    'properties': {
                        'pet_type': {
                            'type': 'string'
                        },
                        'name': {
                            'type': 'string'
                        }
                    }
                },
                'Dog': {
                    'type': 'object',
                    'additionalProperties': False,
                    'required': [
                        'pet_type'
                    ],
                    'properties': {
                        'pet_type': {
                            'type': 'string'
                        },
                        'nickname': {
                            'type': 'string'
                        }
                    }
                },
                'Pet': {
                    'type': 'object',
                    'properties': {
                        'pet': {
                            'oneOf': [
                                {
                                    '$ref': '#/schemas/Cat'
                                },
                                {
                                    '$ref': '#/schemas/Dog'
                                }
                            ],
                            'discriminator': {
                                'propertyName': 'pet_type',
                                'mapping': {
                                    '1': '#/schemas/Cat',
                                }
                            }
                        }
                    }
                }
            }
        }

        schema = Object.from_raw(Components, spec)
        prop = PropertyFactory.generate(schema['schemas']['Pet'])

        cat_payload = {
            'pet': {
                'pet_type': '1',
                'name': 'Misty'
            }
        }

        cat = prop.unmarshal(Cursor.from_raw(cat_payload))
        self.assertEqual(cat['pet']['name'], 'Misty')

        dog_payload = {
            'pet': {
                'pet_type': 'Dog',
                'nickname': 'Max'
            }
        }

        dog = prop.unmarshal(Cursor.from_raw(dog_payload))
        self.assertEqual(dog['pet']['nickname'], 'Max')

        unknown_payload = {
            'pet': {
                'pet_type': '2',
                'nickname': 'Max'
            }
        }

        try:
            prop.unmarshal(Cursor.from_raw(unknown_payload))
        except SchemaError as e:
            self.assertTrue("No one of property types are not matched to discriminator value" in str(e))
        else:
            self.fail("MUST failed because object has unknown pet type")

        # Discriminator with inline schemas
        spec = {
            'x-schemas': {
                'Cat': {
                    'type': 'object',
                    'additionalProperties': False,
                    'required': [
                        'pet_type'
                    ],
                    'properties': {
                        'pet_type': {
                            'type': 'string'
                        },
                        'name': {
                            'type': 'string'
                        }
                    }
                },
                'Dog': {
                    'type': 'object',
                    'additionalProperties': False,
                    'required': [
                        'pet_type'
                    ],
                    'properties': {
                        'pet_type': {
                            'type': 'string'
                        },
                        'nickname': {
                            'type': 'string'
                        }
                    }
                }
            },
            'type': 'object',
            'properties': {
                'pet': {
                    'oneOf': [
                        {
                            '$ref': '#/x-schemas/Cat'
                        },
                        {
                            '$ref': '#/x-schemas/Dog'
                        },
                        {
                            'type': 'object',
                            'additionalProperties': False,
                            'required': [
                                'pet_type'
                            ],
                            'properties': {
                                'pet_type': {
                                    'type': 'string'
                                },
                                'last_name': {
                                    'type': 'string'
                                }
                            }
                        }
                    ],
                    'discriminator': {
                        'propertyName': 'pet_type'
                    }
                }
            }
        }

        schema = Object.from_raw(Schema, spec)
        prop = PropertyFactory.generate(schema)

        inline_payload = {
            'pet': {
                'pet_type': 'Inline',
                'last_name': 'Misty'
            }
        }

        try:
            prop.unmarshal(Cursor.from_raw(inline_payload))
        except SchemaError as e:
            self.assertTrue("No one of property types are not matched to discriminator value" in str(e))
        else:
            self.fail("MUST failed because inline schema in oneOf not considered")

    def test_generate_anyOf(self):
        spec = {
            'x-schemas': {
                'Cat': {
                    'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        'name': {
                            'type': 'string'
                        }
                    }
                },
                'Dog': {
                    'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        'nickname': {
                            'type': 'string'
                        }
                    }
                }
            },
            'type': 'object',
            'properties': {
                'pet': {
                    'anyOf': [
                        {
                            '$ref': '#/x-schemas/Cat'
                        },
                        {
                            '$ref': '#/x-schemas/Dog'
                        }
                    ]
                }
            }
        }

        schema = Object.from_raw(Schema, spec)
        prop = PropertyFactory.generate(schema)

        cat_payload = {
            'pet': {
                'name': 'Misty'
            }
        }

        cat = prop.unmarshal(Cursor.from_raw(cat_payload))
        self.assertEqual(cat['pet']['name'], 'Misty')

        dog_payload = {
            'pet': {
                'nickname': 'Max'
            }
        }

        dog = prop.unmarshal(Cursor.from_raw(dog_payload))
        self.assertEqual(dog['pet']['nickname'], 'Max')

        not_any_payload = {
            'pet': {
                'weight': '10kg'
            }
        }

        try:
            prop.unmarshal(Cursor.from_raw(not_any_payload))
        except SchemaError as e:
            self.assertEqual(
                e.errors,
                {
                    "pet": {
                        "__any__": [
                            {"weight": "Unexpected additional property"},
                            {"weight": "Unexpected additional property"}
                        ]
                    }
                }
            )
        else:
            self.fail("MUST failed because payload not match for all of schemas")

        spec = {
            'x-schemas': {
                'Cat': {
                    'type': 'object',
                    'properties': {
                        'name': {
                            'type': 'string'
                        }
                    }
                },
                'Dog': {
                    'type': 'object',
                    'properties': {
                        'nickname': {
                            'type': 'string'
                        }
                    }
                }
            },
            'type': 'object',
            'properties': {
                'pet': {
                    'anyOf': [
                        {
                            '$ref': '#/x-schemas/Cat'
                        },
                        {
                            '$ref': '#/x-schemas/Dog'
                        }
                    ]
                }
            }
        }

        schema = Object.from_raw(Schema, spec)
        prop = PropertyFactory.generate(schema)

        cat_dog_payload = {
            'pet': {
                'name': 'Misty',
                'nickname': 'Max'
            }
        }

        cat_dog = prop.unmarshal(Cursor.from_raw(cat_dog_payload))
        self.assertEqual(cat_dog['pet']['name'], 'Misty')
        self.assertEqual(cat_dog['pet']['nickname'], 'Max')

    def test_generate_allOf(self):
        spec = {
            'x-schemas': {
                'Cat': {
                    'type': 'object',
                    'properties': {
                        'name': {
                            'type': 'string'
                        },
                        's': {
                            'type': 'integer'
                        }
                    }
                },
                'Dog': {
                    'type': 'object',
                    'properties': {
                        'nickname': {
                            'type': 'string'
                        }
                    }
                }
            },
            'type': 'object',
            'properties': {
                'pet': {
                    'allOf': [
                        {
                            '$ref': '#/x-schemas/Cat'
                        },
                        {
                            '$ref': '#/x-schemas/Dog'
                        }
                    ]
                }
            }
        }

        schema = Object.from_raw(Schema, spec)
        prop = PropertyFactory.generate(schema)

        cat_dog_payload = {
            'pet': {
                'name': 'Misty',
                'nickname': 'Max',
                's': '45'
            }
        }

        cat_dog = prop.unmarshal(Cursor.from_raw(cat_dog_payload), context=Context(strict=False))
        self.assertEqual(cat_dog['pet']['name'], 'Misty')
        self.assertEqual(cat_dog['pet']['nickname'], 'Max')
        self.assertTrue(isinstance(cat_dog['pet']['s'], int))

    def test_generate_recursive_property(self):
        spec = {
            'properties': {
                'payload': {},
                'nested_nodes': {
                    'type': 'array',
                    'items': {
                        '$ref': '#/'
                    }
                }
            }
        }

        schema = Object.from_raw(Schema, spec)
        prop = PropertyFactory.generate(schema)

        payload = {
            'adsad': 'sdsd',
            'payload': {
                'ddd': 34
            },
            'nested_nodes': [
                {
                    'payload': {},
                    'nested_nodes': [
                        {
                            'payload': {
                                'fdf': 54
                            }
                        }
                    ]
                },
                {
                    'payload': {
                        'ff': 'dd'
                    }
                }
            ]
        }

        root = prop.unmarshal(Cursor.from_raw(payload))
        self.assertEqual(root['adsad'], 'sdsd')

    def test_defaults(self):
        spec = {
            'properties': {
                'with_default': {
                    'type': 'integer',
                    'default': 5
                }
            }
        }

        schema = Object.from_raw(Schema, spec)
        prop = PropertyFactory.generate(schema)

        payload = {}

        obj = prop.unmarshal(Cursor.from_raw(payload))
        self.assertEqual(obj['with_default'], 5)

        spec = {
            'properties': {
                'with_default': {
                    'type': 'string',
                    'pattern': '^\+?\d{7,20}$',
                    'default': 'sdfdf'
                }
            }
        }

        schema = Object.from_raw(Schema, spec)
        prop = PropertyFactory.generate(schema)

        payload = {}

        try:
            prop.unmarshal(Cursor.from_raw(payload))
        except SchemaError as e:
            self.assertEqual(e.errors, {"with_default": ["Value did not match to pattern"]})
        else:
            self.fail("MUST failed because default value doesn't match to pattern")

    def test_enum_primitive(self):
        spec = {
            'properties': {
                'prop': {
                    'type': 'integer',
                    'enum': [5, 'ret', '56']
                }
            }
        }

        schema = Object.from_raw(Schema, spec)
        prop = PropertyFactory.generate(schema)

        payload = {
            'prop': 5
        }

        obj = prop.unmarshal(Cursor.from_raw(payload))
        self.assertEqual(obj['prop'], 5)

        payload = {
            'prop': 45
        }

        try:
            prop.unmarshal(Cursor.from_raw(payload))
        except SchemaError as e:
            self.assertEqual(e.errors, {"prop": ["Value is invalid. Expected one of: 5, ret, 56"]})
        else:
            self.fail("MUST failed because property value doesn't match to enumerated values")

        spec = {
            'properties': {
                'prop': {
                    'type': 'string',
                    'enum': ['5', 'ret', '56']
                }
            }
        }

        schema = Object.from_raw(Schema, spec)
        prop = PropertyFactory.generate(schema)

        payload = {
            'prop': '5'
        }

        obj = prop.unmarshal(Cursor.from_raw(payload))
        self.assertEqual(obj['prop'], '5')

        spec = {
            'properties': {
                'prop': {
                    'type': 'boolean',
                    'enum': [True]
                }
            }
        }

        schema = Object.from_raw(Schema, spec)
        prop = PropertyFactory.generate(schema)

        payload = {
            'prop': True
        }

        obj = prop.unmarshal(Cursor.from_raw(payload))
        self.assertEqual(obj['prop'], True)

    def test_enum_list(self):
        spec = {
            'properties': {
                'prop': {
                    'type': 'array',
                    'items': {
                        'type': 'integer'
                    },
                    'enum': [[3], [1, 4]]
                }
            }
        }

        schema = Object.from_raw(Schema, spec)
        prop = PropertyFactory.generate(schema)

        payload = {
            'prop': [3]
        }

        obj = prop.unmarshal(Cursor.from_raw(payload))
        self.assertEqual(obj['prop'], [3])

        payload = {
            'prop': [1, 4]
        }

        obj = prop.unmarshal(Cursor.from_raw(payload))
        self.assertEqual(obj['prop'], [1, 4])

        payload = {
            'prop': [1, 45]
        }

        try:
            prop.unmarshal(Cursor.from_raw(payload))
        except SchemaError as e:
            self.assertEqual(e.errors, {"prop": ["Value is invalid. Expected one of: [3], [1, 4]"]})
        else:
            self.fail("MUST failed because property value doesn't match to enumerated values")

    def test_enum_object(self):
        spec = {
            'properties': {
                'prop': {
                    'type': 'object',
                    'additionalProperties': False,
                    'properties': {
                        'type': {
                            'type': 'integer',
                            'nullable': True
                        }
                    },
                    'enum': [{'type': 0}, {'type': None}]
                }
            }
        }

        schema = Object.from_raw(Schema, spec)
        prop = PropertyFactory.generate(schema)

        payload = {
            'prop': {
                'type': 0
            }
        }

        obj = prop.unmarshal(Cursor.from_raw(payload))
        self.assertEqual(obj['prop']['type'], 0)

        payload = {
            'prop': {
                'type': None
            }
        }

        obj = prop.unmarshal(Cursor.from_raw(payload))
        self.assertEqual(obj['prop']['type'], None)

        payload = {
            'prop': {
                'type': 1
            }
        }

        try:
            prop.unmarshal(Cursor.from_raw(payload))
        except SchemaError as e:
            self.assertTrue('Expected one of' in str(e))
        else:
            self.fail("MUST failed because property value doesn't match to enumerated values")

    def test_required(self):
        spec = {
            'required': ['prop'],
            'properties': {
                'prop': {
                    'type': 'object',
                    'required': ['subprop'],
                    'properties': {
                        'subprop': {
                            'type': 'integer'
                        }
                    }
                }
            }
        }

        schema = Object.from_raw(Schema, spec)
        prop = PropertyFactory.generate(schema)

        payload = {
            'prop': {
                'subprop': 314
            }
        }

        obj = prop.unmarshal(Cursor.from_raw(payload))
        self.assertEqual(obj['prop']['subprop'], 314)

        payload = {
        }

        try:
            prop.unmarshal(Cursor.from_raw(payload))
        except SchemaError as e:
            self.assertEqual(e.errors, {"prop": ["Missing value of required property"]})
        else:
            self.fail("MUST failed because property is required")

        payload = {
            'prop': {}
        }

        try:
            prop.unmarshal(Cursor.from_raw(payload))
        except SchemaError as e:
            self.assertEqual(e.errors, {"prop": {"subprop": ["Missing value of required property"]}})
        else:
            self.fail("MUST failed because sub property is required")

    def test_nullable(self):
        spec = {
            'properties': {
                'prop': {
                    'type': 'integer',
                    'nullable': True
                }
            }
        }

        schema = Object.from_raw(Schema, spec)
        prop = PropertyFactory.generate(schema)

        payload = {
            'prop': None
        }

        obj = prop.unmarshal(Cursor.from_raw(payload))
        self.assertEqual(obj['prop'], None)

        spec = {
            'properties': {
                'prop': {
                    'type': 'integer',
                    'nullable': False
                }
            }
        }

        schema = Object.from_raw(Schema, spec)
        prop = PropertyFactory.generate(schema)

        payload = {
            'prop': None
        }

        try:
            prop.unmarshal(Cursor.from_raw(payload))
        except SchemaError as e:
            self.assertTrue("Property not allow null values" in str(e))
        else:
            self.fail("MUST failed because null values not allowed")

    def test_strict(self):
        spec = {
            'allOf': [
                {'type': 'integer'},
                {'type': 'string'}
            ]
        }

        schema = Object.from_raw(Schema, spec)
        prop = PropertyFactory.generate(schema)

        payload = 5

        try:
            prop.unmarshal(Cursor.from_raw(payload))
        except SchemaError as e:
            self.assertEqual(
                e.errors,
                {"__all__": [["Couldn't interpret value as string"]]}
            )
        else:
            self.fail("MUST failed because payload is not string")

        payload = 5

        obj = prop.unmarshal(Cursor.from_raw(payload), context=Context(strict=False))
        self.assertEqual(obj, '5')

    def test_date(self):
        today = datetime.datetime.now().date()

        spec = {
            'properties': {
                'date': {
                    'type': 'string',
                    'format': 'date',
                }
            }
        }

        schema = Object.from_raw(Schema, spec)
        prop = PropertyFactory.generate(schema)

        payload = {
            'date': today.isoformat()
        }

        obj = prop.unmarshal(Cursor.from_raw(payload))
        self.assertEqual(obj['date'], today)

    def test_datetime(self):
        now = datetime.datetime.now().replace(microsecond=0)

        spec = {
            'properties': {
                'datetime': {
                    'type': 'string',
                    'format': 'date-time',
                }
            }
        }

        schema = Object.from_raw(Schema, spec)
        prop = PropertyFactory.generate(schema)

        payload = {
            'datetime': rfc3339.rfc3339(now)
        }

        obj = prop.unmarshal(Cursor.from_raw(payload))
        self.assertEqual(obj['datetime'], now)

    def test_min_max_properties(self):
        spec = {
            'additionalProperties': True,
            'minProperties': 2,
            'maxProperties': 4,
            'properties': {
                'prop1': {'type': 'string'}
            }
        }

        schema = Object.from_raw(Schema, spec)
        prop = PropertyFactory.generate(schema)

        payload = {
            'prop1': 'abracadabra',
            'prop2': 2
        }

        obj = prop.unmarshal(Cursor.from_raw(payload))
        self.assertEqual(obj['prop1'], 'abracadabra')
        self.assertEqual(obj['prop2'], 2)

        payload = {
            'prop1': 'abracadabra'
        }

        try:
            prop.unmarshal(Cursor.from_raw(payload))
        except SchemaError as e:
            self.assertEqual(e.errors, ["Object does not have enough properties"])
        else:
            self.fail("MUST failed because properties count less than specified in `minProperties`")

        payload = {
            'prop1': 'abracadabra',
            'prop2': 2,
            'prop3': 3,
            'prop4': 4,
            'prop5': 5
        }

        try:
            prop.unmarshal(Cursor.from_raw(payload))
        except SchemaError as e:
            self.assertEqual(e.errors, ["Object has too many properties"])
        else:
            self.fail("MUST failed because properties count more than specified in `maxProperties`")

    def test_styles(self):
        primitive = '5'
        lst = ['3', '4', '5']
        obj = {'role': 'admin', 'firstName': 'Alex'}
        self.assertEqual(factories.style_simple_primitive('5', True), primitive)
        self.assertEqual(factories.style_simple_primitive('5', False), primitive)
        self.assertEqual(factories.style_simple_array('3,4,5', True), lst)
        self.assertEqual(factories.style_simple_array('3,4,5', False), lst)
        self.assertEqual(factories.style_simple_objects('role,admin,firstName,Alex', False), obj)
        self.assertEqual(factories.style_simple_objects('role=admin,firstName=Alex', True), obj)
        self.assertEqual(factories.style_label_primitive('.5', True), primitive)
        self.assertEqual(factories.style_label_primitive('.5', False), primitive)
        self.assertEqual(factories.style_label_array('.3.4.5', True), lst)
        self.assertEqual(factories.style_label_array('.3,4,5', False), lst)
        self.assertEqual(factories.style_label_object('.role=admin.firstName=Alex', True), obj)
        self.assertEqual(factories.style_label_object('.role,admin,firstName,Alex', False), obj)
        self.assertEqual(factories.style_matrix_primitive(';id=5', True), primitive)
        self.assertEqual(factories.style_matrix_primitive(';id=5', False), primitive)
        self.assertEqual(factories.style_matrix_array(';id=3;id=4;id=5', True), lst)
        self.assertEqual(factories.style_matrix_array(';id=3,4,5', False), lst)
        self.assertEqual(factories.style_matrix_object(';role=admin;firstName=Alex', True), obj)
        self.assertEqual(factories.style_matrix_object(';id=role,admin,firstName,Alex', False), obj)
        self.assertEqual(factories.style_form_primitive('5', True), primitive)
        self.assertEqual(factories.style_form_primitive('5', False), primitive)
        self.assertEqual(factories.style_form_array(lst, True), lst)
        self.assertEqual(factories.style_form_array('3,4,5', False), lst)
        self.assertEqual(factories.style_form_object('role,admin,firstName,Alex', False), obj)
        self.assertEqual(factories.style_space_delimited_array('3 4 5', False), lst)
        self.assertEqual(factories.style_pipe_delimited_array('3|4|5', False), lst)

    def test_polymorphic(self):
        spec = {
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
                        }
                    },
                    "required": [
                        "name",
                        "petType"
                    ]
                },
                "Cat": {
                    "description": (
                        "A representation of a cat. Note that `Cat` will be used as the discriminator value."),
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
                    "description": (
                        "A representation of a dog. Note that `Dog` will be used as the discriminator value."),
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

        schema = Object.from_raw(Components, spec)
        prop = PropertyFactory.generate(schema['schemas']['Pet'])

        payload = {
            "petType": "Cat",
            "name": "Misty",
            "huntingSkill": "adventurous",
            "age": 3
        }

        cat = prop.unmarshal(Cursor.from_raw(payload))
        self.assertEqual(cat['age'], 3)
        self.assertEqual(cat['name'], "Misty")
        self.assertEqual(cat['huntingSkill'], "adventurous")

        payload = {
            "petType": "Dog",
            "name": "Max",
            "packSize": 314,
            "age": 2
        }

        dog = prop.unmarshal(Cursor.from_raw(payload))
        self.assertEqual(dog['age'], 2)
        self.assertEqual(dog['name'], "Max")
        self.assertEqual(dog['packSize'], 314)

        payload = {
            "age": 3
        }

        try:
            prop.unmarshal(Cursor.from_raw(payload))
        except SchemaError as e:
            self.assertEqual(e.errors, ["Could't discriminate type. Property with name `petType` not found"])
        else:
            self.fail("MUST failed because `petType` not specified")

        payload = {
            "petType": "Cat",
            "name": "Misty"
        }

        try:
            prop.unmarshal(Cursor.from_raw(payload))
        except SchemaError as e:
            self.assertEqual(
                e.errors,
                {"__all__": [{"huntingSkill": ["Missing value of required property"]}]}
            )
        else:
            self.fail("MUST failed because `huntingSkill` property of `Cat` schema is not specified")


if __name__ == '__main__':
    unittest.main()
