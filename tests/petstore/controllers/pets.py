import falcon


def sequence(start=0):
    while True:
        start += 1
        yield start


class PetStore(object):

    def __init__(self):
        self._data = []
        self._index = {}
        self._sequence = sequence()

    def new_pet(self, name):
        pet = {
            'id': next(self._sequence),
            'name': name,
        }
        self._data.append(pet)
        self._index[pet['id']] = pet
        return pet

    def get_pet(self, pet_id):
        return self._index[pet_id]

    def delete_pet(self, pet_id):
        self._data.remove(self._index[pet_id])
        del self._index[pet_id]

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


store = PetStore()


class Pets(object):

    def on_get(self, req, resp):
        resp.media = [pet for pet in store]

    def on_post(self, req, resp):
        resp.media = store.new_pet(req.content['name'])


class Pet(object):

    def on_get(self, req, resp, **params):
        resp.media = store.get_pet(req.path_params['id'])

    def on_delete(self, req, resp, **params):
        try:
            store.delete_pet(req.path_params['id'])
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
        resp.media = req.content['photo'].filename


class TestUrlencoded(object):

    def on_post(self, req, resp, **params):
        resp.media = [req.content['id'], req.content['file_name']]


class TestStyles(object):

    def on_get(self, req, resp, **params):
        from hic_falcon_heavy._compat import Mapping  # noqa
        x = req.query_params['x']
        resp.media = dict(x) if isinstance(x, Mapping) else x


class TestBase64(object):

    def on_post(self, req, resp, **params):
        from six.moves import StringIO  # noqa
        from hic_falcon_heavy.utils.encoding import Base64EncodableStream  # noqa
        resp.media = {
            'file': Base64EncodableStream(StringIO('Hello human')),
            'input_decoded_file': req.content['file'].read().decode('utf-8')
        }
        resp.set_headers({
            'X-Rate-Limit-Limit': 10,
            'X-Rate-Limit-Remaining': 10,
            'X-Rate-Limit-Reset': 10
        })
