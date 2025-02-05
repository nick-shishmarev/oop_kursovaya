import requests


class VKAPIClient:
    # Доступ к API VK
    API_BASE_URL = r'https://api.vk.com/method'

    def __init__(self, token: str, version='5.191'):
        self.token = token
        self.user_id = None
        self.version = version

    def _common_params(self):
        # Общие обязательные параметры методов
        return {
            'access_token': self.token,
            'v': self.version,
        }

    def method_url(self, api_method: str, params: dict):
        # вызов методов API VK с передачей нужных параметров
        pars = self._common_params()
        pars.update(params)
        response = requests.get(
            f'{self.API_BASE_URL}/{api_method}',
            params=pars
        )
        return response.json()

    def get_user(self, user, fields):
        pars = self._common_params()
        pars.update({'user_ids': user, 'fields': fields})
        response = self.method_url('users.get', pars)

        if response.get('response'):
            self.user_id = response['response'][0]['id']
        else:
            raise ValueError(f"User authorization failed: access_token is not valid")

        return response['response'][0]


class YaDisk:
    # Доступ к API ЯндексДиск
    YA_DSK_URL = 'https://cloud-api.yandex.net/v1/disk/resources'

    def __init__(self, token):
        self.token = token

    def make_folder(self, folder_name: str):
        # Создание папки на ЯндексДиске
        url = self.YA_DSK_URL
        params = {
            'path': folder_name
        }
        headers = {
            'Authorization': self.token
        }
        response = requests.put(url, params=params, headers=headers)

        return response.status_code

    def upload_file(self, folder_name: str, file_name: str, content):
        # Загрузка файла в папку на ЯндексДиске
        url = self.YA_DSK_URL
        method = '/upload'
        params = {
            'path': f'{folder_name}/{file_name}'
        }
        headers = {
            'Authorization': self.token
        }
        f_name = file_name
        response = requests.get(url + method, headers=headers, params=params)

        if response.status_code == 409:
            i = 0
            while response.status_code != 200:
                i += 1
                f_name = f'({i}).'.join(file_name.split('.'))
                params = {
                    'path': f'{folder_name}/{f_name}'
                }
                response = requests.get(url + method, headers=headers, params=params)

        elif response.status_code != 200:
            return response.status_code, response.json().get('message')

        upload_url = response.json()['href']
        response = requests.put(upload_url, files={'file': content})

        return response.status_code, f_name


class VKUser:
    # Информация о пользователе VK
    API_BASE_URL = r'https://api.vk.com/method'

    def __init__(self):
        self.id = None
        self.first_name = None
        self.last_name = None
        self.user_city = None
        self.user_birthday = None
        self.albums = []

    def get_user(self, client, user_id):
        self.id = None
        self.first_name = None
        self.last_name = None
        self.user_city = None
        self.user_birthday = None
        self.albums = []

        fields = 'bdate, city'

        user = client.get_user(user_id, fields)

        if not user:
            return None

        self.id = user['id']
        self.first_name = user['first_name']
        self.last_name = user['last_name']
        self.user_city = user.get('city')['title']
        self.user_birthday = user.get('bdate')

    def get_albums(self, client):
        parameters = {
            'owner_id': self.id,
        }

        albums = client.method_url('photos.getAlbums', parameters)
        if list(albums.keys())[0] == 'response':
            self.albums = albums.get('response').get('items')
            return True
        return False
