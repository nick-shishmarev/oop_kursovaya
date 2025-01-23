import configparser
import json
from datetime import datetime as dt

import requests
import logging
from tqdm import tqdm
from modules import VKAPIClient
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


def get_photos(client, album_name, number):
    # Возвращает список из {number} фото, отсортированных по убыванию размера
    # или код и текст ошибки
    album_id = album_name
    album_lst = ('profile', 'wall', 'saved')        # ID системных альбомов
    if album_name not in album_lst:
        album_id, txt = find_album(client, album_name)
        if not album_id:
            return 0, txt

    out_lst = []

    parameters = {
        'owner_id': client.user_id,
        'album_id': album_id,
        'extended': '1',
        'rev': '1',
    }
    pictures = client.method_url('photos.get', parameters)
    if list(pictures.keys())[0] == 'error':
        err_text = (f"{pictures['error']['error_code']}: "
                    f"{pictures['error']['error_msg']}")

        return 0, err_text

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

    return out_lst[:number]


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


def main():
    config = configparser.ConfigParser()
    config.read('settings.ini')
    vk_token = config['tokens']['vk_token']
    ya_key = config['tokens']['ya_token']
    default_folder = config['folders']['target']
    default_album = config['folders']['vk_album']
    json_f_name = 'files.json'
    photo_json = []
    #
    #
    logging.basicConfig(
        level=logging.INFO,
        filename='log.log',
        encoding='utf-8',
        filemode='a',
        format='[%(asctime)s] %(levelname)s - %(message)s'
    )

    while True:
        user_id = input('VK ID (пустая строка для завершения): ').strip()
        if user_id == '':
            break
        folder_name = input(f'Имя папки на Яндекс_Диске ({default_folder}): ').strip() or default_folder
        number_photos = input('Количество файлов(5): ').strip()
        a_name = input(f'Имя альбома (по умолчанию - {default_album}): ').strip() or default_album
        try:
            number_photos = int(number_photos)
        except ValueError:
            number_photos = 5

        vk_client = VKAPIClient(vk_token, user_id)
        ya_client = YaDisk(ya_key)

        pic_lst = get_photos(vk_client, a_name, number_photos)
        if len(pic_lst) == 0:
            logging.warning(f"Альбом {a_name} пустой")
            print(f"Альбом {a_name} пустой")
            continue
        if pic_lst[0] == 0:
            logging.error(f"Ошибка - {pic_lst[1]}")
            print(f"Ошибка - {pic_lst[1]}")
        else:
            pic_lst = make_lst(pic_lst)
            if len(pic_lst):
                status = ya_client.make_folder(folder_name)
                if status == 201:
                    logging.info(f"Создание папки {folder_name} на Яндекс_Диске  - успешно")
                elif status == 409:
                    logging.info(f"Папка {folder_name} уже существует, добавляем в неё")
                else:
                    logging.error(f"Ошибка не удалось создать папку {folder_name}")
                    print(f"Ошибка не удалось создать папку {folder_name}")
                    break

                for photo, size, url in tqdm(pic_lst):
                    f_name = photo

                    f_content = requests.get(url).content
                    status, txt = ya_client.upload_file(
                        folder_name,
                        f_name,
                        f_content
                    )
                    if status == 201:
                        f_name = txt
                        logging.info(f"Загрузка {photo} в {folder_name} - успешно, имя файла - {f_name}")
                        photo_json.append({
                            'filename': f_name,
                            'size': size
                        })
                    else:
                        logging.error(f"Загрузка {f_name} в {folder_name} -  - ошибка: {txt}")

    with open(json_f_name, 'w') as fp:
        json.dump(photo_json, fp)


if __name__ == '__main__':
    main()
