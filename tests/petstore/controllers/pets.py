import falcon


def sequence(start):
    while True:
        start += 1
        yield start


class PetStore(object):

    def __init__(self):
        self._data = []
        self._index = {}
        self._sequence = sequence(0)

    def new_pet(self, name):
        pet = {
            'id': next(self._sequence),
            'name': name,
        }
        self._data.append(pet)
        self._index[pet['id']] = pet
        return pet

    def get_pet(self, id_):
        return self._index[id_]

    def delete_pet(self, id_):
        self._data.remove(self._index[id_])
        del self._index[id_]

    def __iter__(self):
        return iter(self._data)


def pet(id_, name, tag=None):
    result = {
        'id': id_,
        'name': name
    }
    if tag is not None:
        result['tag'] = tag
    return result


pet_store = PetStore()


class Pets(object):

    def on_get(self, req, resp):
        resp.media = [pet for pet in pet_store]

    def on_post(self, req, resp):
        resp.media = pet_store.new_pet(req.body['name'])


class Pet(object):

    def on_get(self, req, resp, **params):
        resp.media = pet_store.get_pet(req.path_params['id'])

    def on_delete(self, req, resp, **params):
        try:
            pet_store.delete_pet(req.path_params['id'])
        except KeyError:
            resp.status = falcon.HTTP_500
            resp.media = {
                'code': 314,
                'message': "Pet already deleted"
            }
            return
        resp.status = falcon.HTTP_204


class TestMultipart(object):

    def on_post(self, req, resp, **params):
        resp.media = req.body['photo'].filename


class TestUrlencoded(object):

    def on_post(self, req, resp, **params):
        resp.media = [req.body['id'], req.body['file_name']]


class TestStyles(object):

    def on_get(self, req, resp, **params):
        from falcon_heavy.schema.compat import Mapping  # noqa
        x = req.query_params['x']
        resp.media = dict(x) if isinstance(x, Mapping) else x


class TestBase64(object):

    def on_post(self, req, resp, **params):
        from six.moves import StringIO  # noqa
        from falcon_heavy.utils import Base64EncodableStream  # noqa
        resp.media = {
            'file': Base64EncodableStream(StringIO('Hello human')),
            'input_decoded_file': req.body['file'].read().decode('utf-8')
        }
        resp.set_headers({
            'X-Rate-Limit-Limit': 10,
            'X-Rate-Limit-Remaining': 10,
            'X-Rate-Limit-Reset': 10
        })
