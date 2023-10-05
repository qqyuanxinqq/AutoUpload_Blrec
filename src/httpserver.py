from http.server import SimpleHTTPRequestHandler, HTTPServer
import json
import logging
import os

from .Live import Live
from .Myproc import Myproc

from .blive_upload import configured_upload

class MyHandler(SimpleHTTPRequestHandler):

    data_store = {}
    video_list_path = ""
    upload_log_dir = ""
    upload_list = []
    
    @classmethod
    def config(cls, video_list_path,upload_log_dir, upload_config_path):
        cls.video_list_path = video_list_path 
        cls.upload_log_dir = upload_log_dir
        cls.upload_config_path = upload_config_path

    @classmethod
    def set_upload_list(cls):
        with open("upload_config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        cls.upload_list = list(config.keys())


    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        try:
            # Deserialize the JSON payload
            event = json.loads(post_data)
            self.handle_event(event)

        except Exception as e:
            logging.exception(e)


        # You might want to send a response back to the client
        # Here, we send a simple "OK" text.
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK')

    @staticmethod
    def handle_event(event):
        # Extract the event type
        event_type = event.get("type", "")        

        print(event_type)
        if event_type == "RecordingStartedEvent":
            MyHandler.handle_recording_started(event)
            MyHandler.set_upload_list()
            MyHandler.upload(event)

        elif event_type == "RoomChangeEvent":
            MyHandler.handle_room_change(event)
        elif event_type in ["RecordingFinishedEvent", "RecordingCancelledEvent"]:
            MyHandler.handle_recording_finished(event)
        elif event_type == "VideoPostprocessingCompletedEvent":
            MyHandler.handle_video_file_completed(event)
        elif event_type == "Error":
            logging.error(f"Error event occurred at {event['date']}. Error message: {event['data']}")
        else:
            pass

    @classmethod
    def upload(cls, event):
        """
        Upload the video to Bilibili, if room_id is in upload_list.
        """

        room_id = event['data']['room_info']['room_id']
        if str(room_id) in cls.upload_list:
            logfile = os.path.join(
                cls.upload_log_dir,
                os.path.basename(cls.data_store[room_id]).split('.')[0] + '.log'
                )
            p = Myproc(target = configured_upload, args = (cls.data_store[room_id], cls.upload_config_path), name="[{}]Uploader".format(room_id))
            p.set_output_err(logfile)
            p.start()
            p.post_run()
            print("=============================")
            print("开始上传"+ str(room_id))
            print("=============================")
        else:
            logging.warning(f"upload: Room {room_id} not found in upload list{cls.upload_list}")
        
    @classmethod
    def handle_recording_started(cls, event:dict):
        live = Live()
        room_id = event['data']['room_info']['room_id']
        live.create_v1(
                room_id = room_id,
                start_time = event['date'],
                live_title = event['data']['room_info']['title'],
                status="Living"
                )
        live.dump(path = MyHandler.video_list_path)
        cls.data_store[room_id] = live.dump(path = MyHandler.video_list_path)

    @classmethod
    def handle_room_change(cls, event:dict):
        room_id = event['data']['room_info']['room_id']
        if room_id in cls.data_store:
            live = Live(filename = cls.data_store[room_id])
            live.update_live_title(event['data']['room_info']['title'])
            live.dump(path = MyHandler.video_list_path)
        else:
            logging.warning(f"handle_room_change: Room {room_id} not found in data store")

    @classmethod
    def handle_recording_finished(cls, event:dict):
        room_id = event['data']['room_info']['room_id']
        if room_id in cls.data_store:
            live = Live(filename = cls.data_store[room_id])
            live.update_live_status("Done")
            live.dump(path = MyHandler.video_list_path)
        else:
            logging.warning(f"handle_recording_finished: Room {room_id} not found in data store")

    @classmethod
    def handle_video_file_completed(cls, event:dict):
        room_id = event['data']['room_id']
        if room_id in cls.data_store:
            live = live = Live(filename = cls.data_store[room_id])
            live.add_video_v1(
                    start_time = event['date'],
                    filename = event['data']['path']
                    )
            live.dump(path = cls.video_list_path)
        else:
            logging.warning(f"handle_video_file_completed: Room {room_id} not found in data store")

    @classmethod
    def shutdown(cls):
        for room_id in cls.data_store:
            live = Live(filename = cls.data_store[room_id])
            live.update_live_status("Done")
            live.dump(path = cls.video_list_path)

