import os
import logging
from http.server import ThreadingHTTPServer 

import toml

from src.httpserver import MyHandler


PORT = 22333

if __name__ == "__main__":
    with open('settings.toml', 'r', encoding='utf-8') as f:
        settings = toml.load(f)
    video_list_path = os.path.join(settings['output']['out_dir'], "_list")
    os.makedirs(video_list_path, exist_ok=True)
    upload_log_dir = os.path.join(settings['logging']['log_dir'],"_upload_log")
    os.makedirs(upload_log_dir, exist_ok = True)

    MyHandler.config(video_list_path, upload_log_dir, "upload_config.json")

    server_address = ('', PORT)
    httpd = ThreadingHTTPServer(server_address, MyHandler)
    print(f"Listening to port {PORT}...", flush=True)
    try:
        httpd.serve_forever()
    except Exception as e:
        logging.exception(e)
    finally:
        MyHandler.shutdown()
        httpd.server_close()
        print("Terminated Gracefully!")