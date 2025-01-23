import requests


class VKAPIClient:
    # Доступ к API VK
    API_BASE_URL = r'https://api.vk.com/method'

    def __init__(self, token: str, user_id: str, version='5.191'):
        self.token = token
        self.user_id = user_id
        self.version = version

    def _common_params(self):
        # Общие обязательные параметры методов
        return {
            'access_token': self.token,
            'v': self.version,
        }

    def method_url(self, api_method: str, params: dict):
        # вызов методов API VK с передачей нужных параметров
        pars = (self._common_params())
        pars.update(params)
        response = requests.get(
            f'{self.API_BASE_URL}/{api_method}',
            params=pars
        )
        return response.json()


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
