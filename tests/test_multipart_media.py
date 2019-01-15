from __future__ import absolute_import, unicode_literals

import os

import json

import unittest
from six import StringIO

import falcon

from hic_falcon_heavy.testing import create_client

from hic_falcon_heavy.testing import encode_multipart
from http.datastructures import FormStorage, FileStorage


class MultipartTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = create_client(os.path.join(os.path.dirname(__file__), 'petstore/schema/petstore.yaml'))

    def test_multipart(self):
        body, headers = encode_multipart((
            ('id', FormStorage('1')),
            ('meta', FormStorage(json.dumps({'name': 'Max'}), content_type='application/json')),
            ('cotleta', FormStorage(json.dumps({'name': 'Jared Leto'}), content_type='application/json')),
            ('cotleta', FormStorage(json.dumps({'name': 'Jared Leto'}), content_type='application/json')),
            ('photo', FileStorage(
                stream=StringIO('cute puppy\t\n\dsfsdfd\r\n'),
                filename='cam.jpg',
                content_type='image/png',
                headers={'X-Rate-Limit-Limit': '1'}
            ))
        ))

        resp = self.client.simulate_post('/test-multipart', body=body, headers=headers)
        self.assertEqual(falcon.HTTP_200, resp.status)
        self.assertEqual(1, self.client.resource.captured_req.content['id'].value)
        self.assertEqual(2, len(self.client.resource.captured_req.content['cotleta']))
        self.assertEqual(u'cam.jpg', self.client.resource.captured_req.content['photo'].filename)
        self.assertEqual(1, self.client.resource.captured_req.content['photo'].headers['x-rate-limit-limit'])

        data, headers = encode_multipart(())

        resp = self.client.simulate_post('/test-multipart', body=data, headers=headers)
        self.assertEqual(resp.status, falcon.HTTP_400)


if __name__ == '__main__':
    unittest.main()
