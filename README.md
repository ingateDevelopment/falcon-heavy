# Falcon Heavy

Дополнение к фреймворку [Falcon](https://falconframework.org/),  позволяющее автоматически валидировать запросы и ответы по спецификации  [OpenApi 3.0.1](https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.1.md)

**Установка**

```
pip install falcon-heavy
```

**Запуск тестов**

```
tox -e py27,py36
```

**Использование**

Для того чтобы включить автоматическую валидацию запросов и ответов по спецификации, необходимо инициализировать приложение, как показано в примере ниже:

```python
import os

from falcon_heavy.api import FalconHeavyApi, RuntimeResourceClassResolver


application = FalconHeavyApi(
    path=os.path.join(os.path.dirname(__file__), 'schema/petstore.yaml'),
    resource_resolver=RuntimeResourceClassResolver(package='tests.petstore'),
)
```

Для того чтобы **Falcon Heavy** узнал какой ресурс использовать и где он лежит, необходимо в спецификации указать его идентификатор в **обязательном** поле `x-resource` так, как показано в примере ниже (тут используется относительный путь до класса):

```yaml
paths:
 /pets:
   x-resource: controllers.pets:Pets
 /pets/{id}:
   x-resource: controllers.pets:Pet
```

а так же определить резолвер ресурсов, унаследовав его от `AbstractResourceResolver`, и передать его экземпляр в метод инициализации приложения как показано в первом примере (используется `RuntimeResourceResolver` для идентификации ресурса по относительному пути до класса). Резолвер ресурсов может возвращать класс ресурса с конструктором, не принимающим аргументов, или callable-объект, который при вызове вернет инстанс ресурса. Это дает возможность использовать параметризованные ресурсы. При инициализации приложения **Falcon Heavy** добавляет в экземпляр каждого идентифицированного ресурса метаданные, используемые для валидации параметров запроса, тела запроса и тела ответа, а так же добавляет ресурс в роутинг.
Распознанные и валидные параметры и тело запроса кладуться в объект запроса:

```python
def on_post(self, req, resp):
    resp.media = pet_store.new_pet(req.body['name'])

def on_get(self, req, resp, **params):
    resp.media = pet_store.get_pet(req.path_params['id'])
```

Параметры get-запроса попадают в `req.query_params`, параметры определенные в шаблоне пути (например `/pets/{id}`) попадают в `req.path_params`, параметры из заголовка - в `req.header_params`, а параметры из куков - в `req.cookie_params`. Параметры и тело запроса определяются не строго, т.е. если в спецификации не описаны get-параметры, но они присутствуют в запросе, то в `req.query_params` будет словарь с сырыми значениями параметров. Тело запроса кладется в атрибут `req.body` и содержит либо медиа, если для типа контента запроса определен обработчик медиа, либо данные формы, либо `req.bounded_stream`, если длина контента запроса больше нуля и `Undefined` в остальных случаях, если в спецификации тело запроса не является обязательным.

Для включения схем безопасности, основанных на спецификации, необходимо унаследовать свой класс middleware от `AbstractAuthMiddleware` с переопределением метода `process_security_requirement` и добавить его экземпляр в стек middleware приложения. Пример:
```python
class AuthMiddleware(AbstractAuthMiddleware): 

    def process_security_requirement(self, security_requirement, req, resp, resource, params):
        if 'cookieAuth' in security_requirement and req.account is None:
            raise FalconHeavyHTTPForbidden()
```
здесь аргумент `security_requirement` - это [Security Requirement Object](https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.1.md#securityRequirementObject).

Для `multipart/form-data` запросов действует ограничение на использование заголовка `Content-Transfer-Encoding`. Если клиент установил для поля формы заголовок `Content-Transfer-Encoding` в `base64` или `quoted-printable`, то это означает, что клиентский код получит уже декодированные данные, а значит в спецификации нужно декларировать поля буд-то никакого кодирования и декодирования не производилось.

Так же следует избегать записи напрямую в `resp.body` или `resp.data`, а использовать встроенный механизм обработки медиа, чтобы доставить валидатору те данные, которые он сможет проверить. См. [Media](http://falcon.readthedocs.io/en/stable/api/media.html)


**Обработка ошибок**

Все пользовательские ошибки должны быть унаследованы от класса `FalconHeavyHTTPError`. Чтобы изменить обработку встроенных в **Falcon Heavy** ошибок, необходимо их добавить в приложение с явно заданной функцией-обработчиком. См. [Error Handling](http://falcon.readthedocs.io/en/stable/api/errors.html)

Пример пользовательской ошибки:

```python
class ApiError(FalconHeavyHTTPError):

    def __init__(self, error_code, error_params=None, headers=None):
        data = {
            'code': error_code
        }

        if error_params is not None:
            data.update({
                'params': error_params
            })

        super(ApiError, self).__init__(status=falcon.HTTP_418, data=data, headers=headers)
```
