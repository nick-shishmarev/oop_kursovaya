import configparser
import json
from datetime import datetime as dt

import requests
import logging
from tqdm import tqdm
from modules import VKAPIClient, VKUser
from modules import YaDisk


def find_album(client, album_name):
    parameters = {
        'owner_id': client.user_id,
    }

    albums = client.method_url('photos.getAlbums', parameters)
    if list(albums.keys())[0] == 'error':
        return 0, albums['error']['error_msg']

    for album in albums.get('response').get('items'):
        if album['title'] == album_name:
            return album['id'], 'Success'
    return 0, 'Album not found'


def get_photos(client, user, album_id):
    # Возвращает список фото, отсортированных по убыванию размера
    # или код и текст ошибки
    # album_id = album_name
    # album_lst = ('profile', 'wall', 'saved')        # ID системных альбомов
    # if album_name not in album_lst:
    #     album_id, txt = find_album(client, album_name)
    #     if not album_id:
    #         return 0, txt

    out_lst = []

    parameters = {
        'owner_id': user.id,
        'album_id': album_id,
        'extended': '1',
        'rev': '1',
    }
    pictures = client.method_url('photos.get', parameters)
    logging.debug(f"{parameters}")
    if list(pictures.keys())[0] == 'error':
        err_text = (f"{pictures['error']['error_code']}, "
                    f"{pictures['error']['error_msg']}")

        return 0, err_text

    logging.debug(f"{pictures.get('response').get('count') or pictures.get('error').get('error_msg')}")
    for pic in pictures.get('response').get('items'):
        if 'orig_photo' not in pic:
            continue

        out_lst.append([
            max(pic['orig_photo']['height'], pic['orig_photo']['width']),
            pic.get('likes')['count'],
            f"{dt.fromtimestamp(pic['date']):%Y%m%d%H%M%S}",
            pic['text'],
            pic['orig_photo']['url'],
        ])

    out_lst.sort(reverse=True)

    return out_lst


def make_lst(pictures_lst):
    lst = []
    likes_lst = [x[1] for x in pictures_lst]

    for size, likes, date, text, url in pictures_lst:
        if likes_lst.count(likes) > 1:
            f_name = f"{likes}_{date}.jpg"
        else:
            f_name = f"{likes}.jpg"

        lst.append((f_name, size, url))

    return lst


def get_user_id(client: VKAPIClient, user: VKUser):
    while True:
        user_id = input('VK ID (пустая строка - завершение): ').strip()
        if user_id == '':
            break
        user.get_user(client, user_id)
        if not user:
            print(f"Пользователь VK {user_id} не найден")
            continue

        print(f"Выбран пользователь VK: {user.first_name} "
              f"{user.last_name} {user.id}")
        flag = input("Подтвердить - пустая строка, любой символ - отказ: ")
        if not flag:
            user.get_albums(client)
            return True

    return False


def get_photos_from_album(client, user):
    albums = [
        ('profile', 'Профиль'),
        ('wall', 'Стена'),
        ('saved', 'Сохранённые'),
    ]
    if user.albums:
        albums += [(album['id'], album['title']) for album in user.albums]

    for i, album in enumerate(albums):
        print(f"{i + 1:3} {album[0]:10} {album[1]}")

    number_photos = 0
    while True:
        album_number = input('Номер альбома (пустая строка - выход): ')
        if not album_number:
            return False
        try:
            album_number = int(album_number)
        except ValueError:
            album_number = 0

        a_id = albums[album_number - 1][0]
        a_name = albums[album_number - 1][1]


        pic_lst = get_photos(client, user, a_id)
        if len(pic_lst) == 0:
            logging.info(f"Альбом {a_name} пустой")
            print(f"Альбом {a_name} пустой")
            continue
        if pic_lst[0] == 0:
            logging.error(f"Ошибка - {pic_lst[1]}")
            print(f"Ошибка - {pic_lst[1]}")
            continue

        print(f"Выбран альбом {a_name}, содержащий {len(pic_lst)} фото")
        txt = 'Сколько файлов загрузить на ЯндексДиск (5) (пустая строка - выбор другого альбома): '
        number_photos = input(txt).strip()

        if not number_photos:
            continue

        try:
            number_photos = int(number_photos)
        except ValueError:
            number_photos = 5
        break

    return make_lst(pic_lst[:number_photos])


def put_to_yandex(client: YaDisk, lst: list, default: str, file_json: list):
    folder_name = input(f'Имя папки на Яндекс_Диске ({default}): ').strip() or default
    status = client.make_folder(folder_name)
    if status == 201:
        logging.info(f"Создание папки {folder_name} на Яндекс_Диске  - успешно")
    elif status == 409:
        logging.info(f"Папка {folder_name} уже существует, добавляем в неё")
    else:
        logging.error(f"Ошибка не удалось создать папку {folder_name}")
        print(f"Ошибка не удалось создать папку {folder_name}")
        return

    for photo, size, url in tqdm(lst):
        f_name = photo

        f_content = requests.get(url).content
        status, txt = client.upload_file(
            folder_name,
            f_name,
            f_content
        )
        if status == 201:
            f_name = txt
            logging.info(f"Загрузка {photo} в {folder_name} - успешно, имя файла - {f_name}")
            file_json.append({
                'filename': f_name,
                'size': size
            })
        else:
            logging.error(f"Загрузка {f_name} в {folder_name} -  - ошибка: {txt}")

    return file_json


def main():
    config = configparser.ConfigParser()
    config.read('settings.ini')
    vk_token = config['tokens']['vk_token']
    ya_key = config['tokens']['ya_token']
    default_folder = config['folders']['target']
    json_f_name = 'files.json'
    photo_json = []

    logging.basicConfig(
        level=logging.INFO,
        filename='log.log',
        encoding='utf-8',
        filemode='a',
        format='[%(asctime)s] %(levelname)s - %(message)s'
    )
    ya_client = YaDisk(ya_key)
    vk_client = VKAPIClient(vk_token)
    vk_user = VKUser()

    while True:
        # Получаем информацию о пользователе и список его альбомов и помещаем её в vk_user
        if not get_user_id(vk_client, vk_user):
            break

        while True:
            # Получаем список фото из указанного альбома пользователя
            pic_lst = get_photos_from_album(vk_client, vk_user)
            if not pic_lst:
                break

            # Записываем фото из полученного альбома в указанную папку на Яндекс Диске
            # и формируем json файл
            photo_json = put_to_yandex(ya_client, pic_lst, default_folder, photo_json)

    with open(json_f_name, 'w') as fp:
        json.dump(photo_json, fp)


if __name__ == '__main__':
    main()
