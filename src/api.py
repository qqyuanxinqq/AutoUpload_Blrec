import requests

def get_room_info(room_id):
    url = "https://api.live.bilibili.com/room/v1/Room/get_info"
    params = {
        'room_id': room_id
    }
    headers = {
        'Accept-Encoding': 'identity',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.62 Safari/537.36',
    }
    response = requests.get(url, params=params, headers=headers)
    return response.json()

def get_title(room_id):
    response = {}
    try:
        response = get_room_info(room_id)
    except Exception as e:
        print(e)

    title = None
    try:
        title = response['data']['title']
    except Exception as e:
        print(response)

    return title

def download_file(url, save_path):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()  # Raise an error for bad status codes
        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        # print(f"Image successfully downloaded: {save_path}")
    except requests.RequestException as e:
        print(f"Failed to download image: {e}")