import sys
import json
import re
import os
import time
import requests
import urllib.parse
import tqdm
import shutil

STEAM_WORKSHOP_URL = "https://steamcommunity.com/sharedfiles/filedetails/?id=3531865152"
STEAM_WORKSHOP_URL = "https://steamcommunity.com/sharedfiles/filedetails/?id=1215678694"
OUTPUT_STEAM_WORKSHOP_MATERIALS_URL_FOLDER_PATH = ""

ROOT_FOLDER_PATH_str = os.getcwd()
RESULTS_FOLDER_PATH_str = os.path.join(ROOT_FOLDER_PATH_str, "results")

# UPDATED: 202508190001_fileext: ADDED - Заголовки из тестового скрипта для Imgur.
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "sec-ch-ua": '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"'
}

def get_make_results_folder_path(folder_title_str):
    output_folder_path = os.path.join(RESULTS_FOLDER_PATH_str, folder_title_str)
    os.makedirs(output_folder_path, exist_ok=True)
    return output_folder_path

def create_write_file_bytes(output_folder, file_name, bytes_content):
    file_path = os.path.join(output_folder, file_name)
    with open(file_path, "wb") as f:
        f.write(bytes_content)
    return file_path

def create_write_file_string(output_folder, file_name, content_str):
    os.makedirs(output_folder, exist_ok=True)
    file_path = os.path.join(output_folder, file_name)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content_str)
    return file_path

# UPDATED: 202508190001_fileext: ADDED - Извлечение всех http/https ссылок до \x00.
def extract_image_urls(workshop_content):
    url_pattern = r'https?://[^\s<>"\']*?(?=\x00|\s|<|>|"|\'|$)'
    raw_urls = re.findall(url_pattern, workshop_content)
    image_urls = list()
    if raw_urls:
        for u in raw_urls:
            if u:
                u = u.split('\x00', 1)[0]
                u = u.strip()
                if u:
                    image_urls.append(u)
    return list(set(image_urls))

# UPDATED: 202508190001_fileext: ADDED - Проверка существующих файлов в папке downloads.
def get_existing_files(downloads_folder):
    if not os.path.exists(downloads_folder):
        return set()
    existing_files = set()
    for filename in os.listdir(downloads_folder):
        base_name = os.path.splitext(filename)[0]
        existing_files.add(base_name)
    return existing_files

# UPDATED: 202508190001_fileext: ADDED - Определение расширения по сигнатуре файла.
# UPDATED: 202508190147_objfix: UPDATED - Исправлена обработка OBJ с помощью isinstance.
def get_file_extension(content, content_type, url):
    parsed_url = urllib.parse.urlparse(url)
    hash_part = parsed_url.path.strip('/').split('/')[-1]
    clean_hash = hash_part.split('?')[0]
    if '.' in clean_hash:
        return f".{clean_hash.split('.')[-1].lower()}"

    # Проверяем байтовые сигнатуры
    if isinstance(content, bytes):
        if content.startswith(b'%PDF-'):
            return ".pdf"
        elif content.startswith(b'\xFF\xD8\xFF'):
            return ".jpg"
        elif content.startswith(b'\x89PNG'):
            return ".png"
        elif content.startswith(b'GIF89a') or content.startswith(b'GIF87a'):
            return ".gif"
        elif content.startswith(b'PK\x03\x04'):
            return ".zip"
        elif content.startswith(b'\x1F\x8B'):
            return ".gz"
        elif content.startswith(b'UnityFS'):
            return ".unity3d"
        elif content.startswith(b'PAK\0'):
            return ".pak"

    # Проверяем текстовые сигнатуры
    try:
        head = content[:200].decode("utf-8", errors="ignore")
        # if head.startswith("#") and (" v " in head or " f " in head or "mtllib" in head):
        #     return ".obj"
        if head.startswith("#") and (" v " in head or "\nv " in head
                                     or " f " in head or "\nf " in head
                                     or "mtllib" in head or "Rhino" in head):
            return ".obj"
        elif head.startswith("#") and "newmtl" in head:
            return ".mtl"
        elif head.lstrip().startswith("; FBX") or "FBXHeaderExtension" in head:
            return ".fbx"
        elif head.startswith("glTF"):
            return ".glb"
        elif head.lstrip().startswith("{") and '"asset"' in head and "version" in head:
            return ".gltf"
        elif head.lstrip().startswith("solid"):
            return ".stl"
        elif all(32 <= c < 127 or c in (10, 13) for c in content[:200] if isinstance(c, int)):
            return ".txt"
    except UnicodeDecodeError:
        pass

    # Проверяем Content-Type
    content_type = content_type.lower()
    if "jpeg" in content_type:
        return ".jpg"
    elif "png" in content_type:
        return ".png"
    elif "text/plain" in content_type:
        return ".txt"
    elif "application/pdf" in content_type:
        return ".pdf"
    elif "image/gif" in content_type:
        return ".gif"

    return ".bin"

def get_request_title_and_cdn_link_from_steam_api(output_folder, steam_workshop_url):
    parsed_url = urllib.parse.urlparse(steam_workshop_url)
    query_params = urllib.parse.parse_qs(parsed_url.query)
    if 'id' not in query_params:
        print("Ошибка: URL не содержит id.")
        sys.exit(1)
    published_file_id = int(query_params['id'][0])

    steam_api_url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
    data = {
        "itemcount": 1,
        "publishedfileids[0]": published_file_id
    }
    response = requests.post(steam_api_url, data=data, headers=BROWSER_HEADERS)
    if response.status_code != 200:
        print(f"Ошибка при получении деталей из Steam API. Код: {response.status_code}, Ответ: {response.text}")
        sys.exit(1)

    parsed_json = json.loads(response.text)
    details = response.json()["response"]["publishedfiledetails"][0]
    cdn_to_download_file_url = details["file_url"]
    if not output_folder:
        results_folder_title_str = details['publishedfileid'] + "_" + details["title"]
        output_folder = get_make_results_folder_path(results_folder_title_str)
        create_write_file_string(output_folder, "api_steampowered_response.json", json.dumps(parsed_json, indent=4, ensure_ascii=False))
        return output_folder, cdn_to_download_file_url
    return output_folder, cdn_to_download_file_url

def get_reponse_imgur_fc(url_str):
    # url_str: 'https://i.imgur.com/GkjyUtj.png'
    headers = {
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    url_str = url_str.replace("/imgur.com/", "/i.imgur.com").replace('http://', 'https://')

    response = requests.get(url_str, headers=headers)
    return response

def get_response_steampowered(url_str):
    '''
    https://cloud-3.steamusercontent.com/ugc/850479464143302624/30B9BF9979ABED6DA3739D33801D670A2C1ED2C9/
    https://steamusercontent-a.akamaihd.net/ugc/850479464143302624/30B9BF9979ABED6DA3739D33801D670A2C1ED2C9/
    :param url_str:
    :return:
    '''

    headers = {
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    file_response = requests.get(url_str, headers=headers, allow_redirects=True)
    if file_response.status_code == 403:
        parsed = urllib.parse.urlparse(url_str)
        updated = parsed._replace(netloc="steamusercontent-a.akamaihd.net")
        new_url = urllib.parse.urlunparse(updated)
        file_response = requests.get(new_url, headers=headers, allow_redirects=True)
    return file_response

def process_fc(workshop_url, output_folder, is_clean=False):
    output_folder, cdn_to_download_file_url = get_request_title_and_cdn_link_from_steam_api(output_folder, workshop_url)
    downloads_folder = os.path.join(output_folder, "downloads")
    cache_file = os.path.join(output_folder, "WorkshopUpload")
    links_file = os.path.join(output_folder, "download_urls.txt")
    log_file = os.path.join(output_folder, "download_urls_log.txt")

    # UPDATED: 202508190001_fileext: ADDED - Удаление всех данных при is_clean=True.
    if is_clean:
        for file_path in [cache_file, links_file, log_file]:
            if os.path.exists(file_path):
                os.remove(file_path)
        if os.path.exists(downloads_folder):
            shutil.rmtree(downloads_folder)
    os.makedirs(downloads_folder, exist_ok=True)

    # UPDATED: 202508190001_fileext: ADDED - Скачивание WorkshopUpload, если не существует.
    workshop_content = None
    if not os.path.exists(cache_file):
        print(f"Скачивание Workshop-файла: {cdn_to_download_file_url}")
        workshop_response = requests.get(cdn_to_download_file_url, headers=BROWSER_HEADERS)
        if workshop_response.status_code != 200:
            print(f"Ошибка при скачивании Workshop-файла: Код {workshop_response.status_code}")
            sys.exit(1)
        workshop_content = workshop_response.text
        create_write_file_string(output_folder, "WorkshopUpload", workshop_content)
    else:
        print(f"WorkshopUpload уже существует: {cache_file}")
        with open(cache_file, "r", encoding="utf-8") as f:
            workshop_content = f.read()

    # UPDATED: 202508190001_fileext: ADDED - Создание downloads_urls.txt при новом WorkshopUpload или если отсутствует.
    if not os.path.exists(links_file) or not os.path.exists(cache_file):
        image_urls = extract_image_urls(workshop_content)
        if not image_urls:
            print("Не найдено ссылок.")
            create_write_file_string(output_folder, "downloads_urls.txt", "")
            sys.exit(0)
        create_write_file_string(output_folder, "downloads_urls.txt", "\n".join(image_urls))
    else:
        print(f"downloads_urls.txt уже существует: {links_file}")
        with open(links_file, "r", encoding="utf-8") as f:
            image_urls = [line.strip() for line in f if line.strip()]

    # UPDATED: 202508190001_fileext: ADDED - Фильтрация ссылок, исключая уже скачанные файлы.
    existing_files = get_existing_files(downloads_folder)
    urls_to_download = []
    for url in image_urls:
        parsed_url = urllib.parse.urlparse(url)
        hash_part = parsed_url.path.strip('/').split('/')[-1]
        clean_hash = hash_part.split('?')[0]
        if clean_hash not in existing_files:
            urls_to_download.append(url)
        else:
            print(f"Пропущен (уже существует): {url}")

    # UPDATED: 202508190001_fileext: UPDATED - Скачивание с определением расширения по сигнатуре.
    print(f"Найдено {len(urls_to_download)} новых файлов для скачивания.")
    with open(log_file, "a", encoding="utf-8") as log:
        for url in tqdm.tqdm(urls_to_download, desc="Скачивание файлов"):
            try:
                time.sleep(1)
                headers = BROWSER_HEADERS.copy()
                if "dropbox.com" in url:
                    parsed_url = urllib.parse.urlparse(url)
                    headers["Dropbox-API-Arg"] = json.dumps({"path": parsed_url.path})

                if "imgur." in url:
                    file_response = get_reponse_imgur_fc(url)
                elif '.steamusercontent.' in url:
                    file_response = get_response_steampowered(url)
                else:
                    file_response = requests.get(url, headers=headers, allow_redirects=True)
                log.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Запрос: {url}\n")
                log.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Content-Type: {file_response.headers.get('Content-Type', '')}\n")
                if file_response.status_code == 200:
                    content_type = file_response.headers.get("Content-Type", "").lower()
                    response_content = file_response.content
                    log.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Первые 200 байт ответа: {response_content[:200].decode('utf-8', errors='ignore')}\n")
                    if "text/html" in content_type:
                        log.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ошибка: Получена HTML-страница вместо файла для {url}\n")
                        continue
                    parsed_url = urllib.parse.urlparse(url)
                    hash_part = parsed_url.path.strip('/').split('/')[-1]
                    clean_hash = hash_part.split('?')[0]
                    ext = get_file_extension(response_content, content_type, url)
                    file_name = clean_hash if '.' in clean_hash else f"{clean_hash}{ext}"
                    file_path = create_write_file_bytes(downloads_folder, file_name, response_content)
                    log.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Успешно скачано: {file_path}\n")
                else:
                    log.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ошибка: Код {file_response.status_code} для {url}\n")
            except Exception as e:
                log.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Ошибка при скачивании {url}: {str(e)}\n")

def main():
    # UPDATED: 202508190001_fileext: ADDED - Проверка флага --clean.
    is_clean = "--clean" in sys.argv
    if is_clean:
        sys.argv.remove("--clean")
        print("Режим очистки активирован: все кэши и логи будут удалены.")

    if len(sys.argv) == 3:
        print("Использование: python script.py [--clean] <workshop_url> <output_folder>")
        workshop_url = sys.argv[1]
        output_folder = sys.argv[2]
        process_fc(workshop_url, output_folder, is_clean)
        sys.exit(1)

    process_fc(STEAM_WORKSHOP_URL, OUTPUT_STEAM_WORKSHOP_MATERIALS_URL_FOLDER_PATH, is_clean)

if __name__ == "__main__":
    main()