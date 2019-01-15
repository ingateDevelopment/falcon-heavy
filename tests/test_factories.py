from __future__ import absolute_import, unicode_literals

import datetime
from contextlib import contextmanager

from six import iteritems

import rfc3339

import unittest

from hic_falcon_heavy.openapi import (
    SchemaObjectType,
    ComponentsObjectType
)
from hic_falcon_heavy.factories.properties import PropertyFactory, PROPERTY_GENERATION_MODE

from hic_falcon_heavy.schema.path import Path
from hic_falcon_heavy.schema.ref_resolver import RefResolver
from hic_falcon_heavy.schema.exceptions import SchemaError, Error


class FactoriesTest(unittest.TestCase):

    @staticmethod
    def _load(object_type, specification):
        return object_type().convert(
            specification,
            Path(''),
            strict=True,
            registry={},
            ref_resolver=RefResolver('', specification)
        )

    @staticmethod
    def _generate_property(schema, mode=PROPERTY_GENERATION_MODE.READ_ONLY):
        factory = PropertyFactory(mode=mode)
        return factory.generate(schema)

    @staticmethod
    def _convert(t, payload, strict=True):
        return t.convert(payload, Path(''), strict=strict)

    @contextmanager
    def assertSchemaErrorRaises(self, expected_errors=None):
        with self.assertRaises(SchemaError) as ctx:
            yield

        if expected_errors is not None:
            self.assertEqual(len(expected_errors), len(ctx.exception.errors))

            for path, message in iteritems(expected_errors):
                self.assertTrue(
                    Error(Path(path), message) in ctx.exception.errors,
                    msg="An error at %s with message \"%s\" was expected, but these errors were received:\n%s" % (
                        path, message, ctx.exception.errors)
                )

    def test_generate_one_of(self):
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

        schema = self._load(SchemaObjectType, spec)
        prop = self._generate_property(schema)

        cat_payload = {
            'pet': {
                'name': 'Misty'
            }
        }

        cat = self._convert(prop, cat_payload)
        self.assertEqual(cat['pet']['name'], 'Misty')

        dog_payload = {
            'pet': {
                'nickname': 'Max'
            }
        }

        dog = self._convert(prop, dog_payload)
        self.assertEqual(dog['pet']['nickname'], 'Max')

    def test_generate_oneof_with_implicit_discriminator(self):
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

        schema = self._load(ComponentsObjectType, spec)
        prop = self._generate_property(schema['schemas']['Pet'])

        cat_payload = {
            'pet': {
                'pet_type': 'Cat',
                'name': 'Misty'
            }
        }

        cat = self._convert(prop, cat_payload)
        self.assertEqual(cat['pet']['name'], 'Misty')
        self.assertEqual(cat['pet']['pet_type'], 'Cat')

        ambiguous_cat_payload = {
            'pet': {
                'pet_type': '',
                'name': 'Misty'
            }
        }

        with self.assertSchemaErrorRaises({
            '#/pet': "The discriminator value should be equal to one of the following values: Cat, Dog"
        }):
            self._convert(prop, ambiguous_cat_payload)

        dog_with_cat_properties = {
            'pet': {
                'pet_type': 'Dog',
                'name': 'Misty'
            }
        }

        with self.assertSchemaErrorRaises({
            '#/pet': "No unspecified properties are allowed."
                     " The following unspecified properties were found: name"
        }):
            self._convert(prop, dog_with_cat_properties)

    def test_generate_one_of_with_semi_explicit_discriminator(self):
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

        schema = self._load(ComponentsObjectType, spec)
        prop = self._generate_property(schema['schemas']['Pet'])

        cat_payload = {
            'pet': {
                'pet_type': '1',
                'name': 'Misty'
            }
        }

        cat = self._convert(prop, cat_payload)
        self.assertEqual(cat['pet']['name'], 'Misty')

        dog_payload = {
            'pet': {
                'pet_type': 'Dog',
                'nickname': 'Max'
            }
        }

        dog = self._convert(prop, dog_payload)
        self.assertEqual(dog['pet']['nickname'], 'Max')

        unknown_payload = {
            'pet': {
                'pet_type': '2',
                'nickname': 'Max'
            }
        }

        with self.assertSchemaErrorRaises({
            '#/pet': "The discriminator value should be equal to one of the following values: 1, Cat, Dog"
        }):
            self._convert(prop, unknown_payload)

    def test_generate_discriminator_with_inline_schemas(self):
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

        schema = self._load(SchemaObjectType, spec)
        prop = self._generate_property(schema)

        inline_payload = {
            'pet': {
                'pet_type': 2,
                'last_name': 'Misty'
            }
        }

        with self.assertSchemaErrorRaises({
            '#/pet': "The discriminator value should be equal to one of the following values: Cat, Dog"
        }):
            self._convert(prop, inline_payload)

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

        schema = self._load(SchemaObjectType, spec)
        prop = self._generate_property(schema)

        cat_payload = {
            'pet': {
                'name': 'Misty'
            }
        }

        cat = self._convert(prop, cat_payload)
        self.assertEqual(cat['pet']['name'], 'Misty')

        dog_payload = {
            'pet': {
                'nickname': 'Max'
            }
        }

        dog = self._convert(prop, dog_payload)
        self.assertEqual(dog['pet']['nickname'], 'Max')

        not_any_payload = {
            'pet': {
                'weight': '10kg'
            }
        }

        with self.assertSchemaErrorRaises({
            '#/pet': "Does not match any schemas from `anyOf`",
            '#/pet/0': "No unspecified properties are allowed."
                       " The following unspecified properties were found: weight",
            '#/pet/1': "No unspecified properties are allowed."
                       " The following unspecified properties were found: weight"
        }):
            self._convert(prop, not_any_payload)

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

        schema = self._load(SchemaObjectType, spec)
        prop = self._generate_property(schema)

        cat_dog_payload = {
            'pet': {
                'name': 'Misty',
                'nickname': 'Max'
            }
        }

        cat_dog = self._convert(prop, cat_dog_payload)
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

        schema = self._load(SchemaObjectType, spec)
        prop = self._generate_property(schema)

        cat_dog_payload = {
            'pet': {
                'name': 'Misty',
                'nickname': 'Max',
                's': '45'
            }
        }

        cat_dog = self._convert(prop, cat_dog_payload, strict=False)
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

        schema = self._load(SchemaObjectType, spec)
        prop = self._generate_property(schema)

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

        root = self._convert(prop, payload)
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

        schema = self._load(SchemaObjectType, spec)
        prop = self._generate_property(schema)

        payload = {}

        obj = self._convert(prop, payload)
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

        schema = self._load(SchemaObjectType, spec)
        prop = self._generate_property(schema)

        payload = {}

        with self.assertSchemaErrorRaises({
            '#/with_default': "Does not match to pattern"
        }):
            self._convert(prop, payload)

    def test_enum_primitive(self):
        spec = {
            'properties': {
                'prop': {
                    'type': 'integer',
                    'enum': [5, 'ret', '56']
                }
            }
        }

        schema = self._load(SchemaObjectType, spec)
        prop = self._generate_property(schema)

        payload = {
            'prop': 5
        }

        obj = self._convert(prop, payload)
        self.assertEqual(obj['prop'], 5)

        payload = {
            'prop': 45
        }

        with self.assertSchemaErrorRaises({
            '#/prop': "Should be equal to one of the allowed values. Allowed values: 5, 56, ret"
        }):
            self._convert(prop, payload)

        spec = {
            'properties': {
                'prop': {
                    'type': 'string',
                    'enum': ['5', 'ret', '56']
                }
            }
        }

        schema = self._load(SchemaObjectType, spec)
        prop = self._generate_property(schema)

        payload = {
            'prop': '5'
        }

        obj = self._convert(prop, payload)
        self.assertEqual(obj['prop'], '5')

        spec = {
            'properties': {
                'prop': {
                    'type': 'boolean',
                    'enum': [True]
                }
            }
        }

        schema = self._load(SchemaObjectType, spec)
        prop = self._generate_property(schema)

        payload = {
            'prop': True
        }

        obj = self._convert(prop, payload)
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

        schema = self._load(SchemaObjectType, spec)
        prop = self._generate_property(schema)

        payload = {
            'prop': [3]
        }

        obj = self._convert(prop, payload)
        self.assertEqual(obj['prop'], [3])

        payload = {
            'prop': [1, 4]
        }

        obj = self._convert(prop, payload)
        self.assertEqual(obj['prop'], [1, 4])

        payload = {
            'prop': [1, 45]
        }

        with self.assertSchemaErrorRaises({
            '#/prop': "Should be equal to one of the allowed values. Allowed values: [1, 4], [3]"
        }):
            self._convert(prop, payload)

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

        schema = self._load(SchemaObjectType, spec)
        prop = self._generate_property(schema)

        payload = {
            'prop': {
                'type': 0
            }
        }

        obj = self._convert(prop, payload)
        self.assertEqual(obj['prop']['type'], 0)

        payload = {
            'prop': {
                'type': None
            }
        }

        obj = self._convert(prop, payload)
        self.assertEqual(obj['prop']['type'], None)

        payload = {
            'prop': {
                'type': 1
            }
        }

        with self.assertSchemaErrorRaises({
            '#/prop': "Should be equal to one of the allowed values. Allowed values: {u'type': 0}, {u'type': None}"
        }):
            self._convert(prop, payload)

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

        schema = self._load(SchemaObjectType, spec)
        prop = self._generate_property(schema)

        payload = {
            'prop': {
                'subprop': 314
            }
        }

        obj = self._convert(prop, payload)
        self.assertEqual(obj['prop']['subprop'], 314)

        payload = {
        }

        with self.assertSchemaErrorRaises({
            '#': "The following required properties are missed: prop"
        }):
            self._convert(prop, payload)

        payload = {
            'prop': {}
        }

        with self.assertSchemaErrorRaises({
            '#/prop': "The following required properties are missed: subprop"
        }):
            self._convert(prop, payload)

    def test_nullable(self):
        spec = {
            'properties': {
                'prop': {
                    'type': 'integer',
                    'nullable': True
                }
            }
        }

        schema = self._load(SchemaObjectType, spec)
        prop = self._generate_property(schema)

        payload = {
            'prop': None
        }

        obj = self._convert(prop, payload)
        self.assertEqual(obj['prop'], None)

        spec = {
            'properties': {
                'prop': {
                    'type': 'integer',
                    'nullable': False
                }
            }
        }

        schema = self._load(SchemaObjectType, spec)
        prop = self._generate_property(schema)

        payload = {
            'prop': None
        }

        with self.assertSchemaErrorRaises({
            '#/prop': "Null values not allowed"
        }):
            self._convert(prop, payload)

    def test_strict(self):
        spec = {
            'allOf': [
                {'type': 'integer'},
                {'type': 'string'}
            ]
        }

        schema = self._load(SchemaObjectType, spec)
        prop = self._generate_property(schema)

        payload = 5

        with self.assertSchemaErrorRaises({
            '#': "Does not match all schemas from `allOf`. Invalid schema indexes: 1",
            '#/1': "Should be a string"
        }):
            self._convert(prop, payload)

        payload = 5

        obj = self._convert(prop, payload, strict=False)
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

        schema = self._load(SchemaObjectType, spec)
        prop = self._generate_property(schema)

        payload = {
            'date': today.isoformat()
        }

        obj = self._convert(prop, payload)
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

        schema = self._load(SchemaObjectType, spec)
        prop = self._generate_property(schema)

        payload = {
            'datetime': rfc3339.rfc3339(now)
        }

        obj = self._convert(prop, payload)
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

        schema = self._load(SchemaObjectType, spec)
        prop = self._generate_property(schema)

        payload = {
            'prop1': 'abracadabra',
            'prop2': 2
        }

        obj = self._convert(prop, payload)
        self.assertEqual(obj['prop1'], 'abracadabra')
        self.assertEqual(obj['prop2'], 2)

        payload = {
            'prop1': 'abracadabra'
        }

        with self.assertSchemaErrorRaises({
            '#': "Object must have at least 2 properties. It had only 1 properties"
        }):
            self._convert(prop, payload)

        payload = {
            'prop1': 'abracadabra',
            'prop2': 2,
            'prop3': 3,
            'prop4': 4,
            'prop5': 5
        }

        with self.assertSchemaErrorRaises({
            '#': "Object must have no more than 4 properties. It had 5 properties"
        }):
            self._convert(prop, payload)

    # def test_styles(self):
    #     primitive = '5'
    #     lst = ['3', '4', '5']
    #     obj = {'role': 'admin', 'firstName': 'Alex'}
    #     self.assertEqual(factories.style_simple_primitive('5', True), primitive)
    #     self.assertEqual(factories.style_simple_primitive('5', False), primitive)
    #     self.assertEqual(factories.style_simple_array('3,4,5', True), lst)
    #     self.assertEqual(factories.style_simple_array('3,4,5', False), lst)
    #     self.assertEqual(factories.style_simple_objects('role,admin,firstName,Alex', False), obj)
    #     self.assertEqual(factories.style_simple_objects('role=admin,firstName=Alex', True), obj)
    #     self.assertEqual(factories.style_label_primitive('.5', True), primitive)
    #     self.assertEqual(factories.style_label_primitive('.5', False), primitive)
    #     self.assertEqual(factories.style_label_array('.3.4.5', True), lst)
    #     self.assertEqual(factories.style_label_array('.3,4,5', False), lst)
    #     self.assertEqual(factories.style_label_object('.role=admin.firstName=Alex', True), obj)
    #     self.assertEqual(factories.style_label_object('.role,admin,firstName,Alex', False), obj)
    #     self.assertEqual(factories.style_matrix_primitive(';id=5', True), primitive)
    #     self.assertEqual(factories.style_matrix_primitive(';id=5', False), primitive)
    #     self.assertEqual(factories.style_matrix_array(';id=3;id=4;id=5', True), lst)
    #     self.assertEqual(factories.style_matrix_array(';id=3,4,5', False), lst)
    #     self.assertEqual(factories.style_matrix_object(';role=admin;firstName=Alex', True), obj)
    #     self.assertEqual(factories.style_matrix_object(';id=role,admin,firstName,Alex', False), obj)
    #     self.assertEqual(factories.style_form_primitive('5', True), primitive)
    #     self.assertEqual(factories.style_form_primitive('5', False), primitive)
    #     self.assertEqual(factories.style_form_array(lst, True), lst)
    #     self.assertEqual(factories.style_form_array('3,4,5', False), lst)
    #     self.assertEqual(factories.style_form_object('role,admin,firstName,Alex', False), obj)
    #     self.assertEqual(factories.style_space_delimited_array('3 4 5', False), lst)
    #     self.assertEqual(factories.style_pipe_delimited_array('3|4|5', False), lst)

    def test_polymorphic(self):
        spec = {
            "schemas": {
                "Pet": {
                    "deprecated": True,
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
                        },
                    ]
                }
            }
        }

        schema = self._load(ComponentsObjectType, spec)
        prop = self._generate_property(schema['schemas']['Pet'])

        payload = {
            "petType": "Cat",
            "name": "Misty",
            "huntingSkill": "adventurous",
            "age": 3
        }

        cat = self._convert(prop, payload)
        self.assertEqual(cat['age'], 3)
        self.assertEqual(cat['name'], "Misty")
        self.assertEqual(cat['huntingSkill'], "adventurous")

        payload = {
            "petType": "Dog",
            "name": "Max",
            "packSize": 314,
            "age": 2
        }

        dog = self._convert(prop, payload)
        self.assertEqual(dog['age'], 2)
        self.assertEqual(dog['name'], "Max")
        self.assertEqual(dog['packSize'], 314)

        payload = {
            "age": 3
        }

        with self.assertSchemaErrorRaises({
            '#': "A property with name 'petType' must be present"
        }):
            self._convert(prop, payload)

        payload = {
            "petType": "Cat",
            "name": "Misty"
        }

        with self.assertSchemaErrorRaises({
            '#': "Does not match all schemas from `allOf`. Invalid schema indexes: 1",
            '#/1': "The following required properties are missed: huntingSkill"
        }):
            self._convert(prop, payload)


if __name__ == '__main__':
    unittest.main()
