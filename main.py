import os
import logging
from http.server import HTTPServer

import toml

from src.httpserver import MyHandler



if __name__ == "__main__":
    with open('settings.toml', 'r') as f:
        settings = toml.load(f)
    video_list_path = os.path.join(settings['output']['out_dir'], "_list")
    os.makedirs(video_list_path, exist_ok=True)
    upload_log_dir = os.path.join(settings['output']['out_dir'],"_upload_log")
    os.makedirs(upload_log_dir, exist_ok = True)

    MyHandler.config(video_list_path, upload_log_dir, "upload_config.json")

    server_address = ('', 22333)
    httpd = HTTPServer(server_address, MyHandler)
    print("Serving on port 22333...")
    try:
        httpd.serve_forever()
    except Exception as e:
        logging.exception(e)
    finally:
        MyHandler.shutdown()
        httpd.server_close()
        print("Terminated Gracefully!")