from http.server import SimpleHTTPRequestHandler, HTTPServer
import json
import logging
import os

from .Live import Live
from .Myproc import Myproc

from .blive_upload import configured_upload

class MyHandler(SimpleHTTPRequestHandler):

    # json file path for each room_id
    room_ids = {}
    videos_active = {}
    lists_fin_wait = set()
    
    _video_list_directory = ""
    _upload_log_dir = ""
    _upload_list = []
    
    @classmethod
    def config(cls, video_list_path,upload_log_dir, upload_config_path):
        cls._video_list_directory = video_list_path 
        cls._upload_log_dir = upload_log_dir
        cls.upload_config_path = upload_config_path

    @classmethod
    def set_upload_list(cls):
        with open("upload_config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        cls._upload_list = list(config.keys())


    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')

        try:
            # Deserialize the JSON payload
            event = json.loads(post_data)
            self.log_event(event)
            self.handle_event(event)

        except Exception as e:
            logging.exception(e)


        # You might want to send a response back to the client
        # Here, we send a simple "OK" text.
        self.send_response_only(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK')

    def log_event(self, event):
        event_type = event.get("type", "")
        if event['data'].get('room_id'):
            room_id = event['data']['room_id']
        elif event['data'].get('room_info'):
            room_id = event['data']['room_info']['room_id']
        else:
            room_id = ""
        format = f"[{room_id}] {event_type}"
        self.log_message(format)

    @staticmethod
    def handle_event(event):
        # Extract the event type
        event_type = event.get("type", "")

        # Handle the event according to its type      
        if event_type == "RecordingStartedEvent":
            MyHandler.handle_recording_started(event)
            MyHandler.set_upload_list()
            MyHandler.upload(event)
        elif event_type == "RoomChangeEvent":
            MyHandler.handle_room_change(event)
        elif event_type in ["RecordingFinishedEvent", "RecordingCancelledEvent"]:
            MyHandler.handle_recording_finished(event)
        elif event_type == "VideoFileCreatedEvent":
            MyHandler.handle_video_create(event)
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

        if str(room_id) in cls._upload_list:
            logfile = os.path.join(
                cls._upload_log_dir,
                os.path.basename(cls.room_ids[room_id]).split('.')[0] + '.log'
                )
            p = Myproc(target = configured_upload, args = (cls.room_ids[room_id], cls.upload_config_path), name="[{}]Uploader".format(room_id))
            p.set_output_err(logfile)
            p.start()
            p.post_run()
            print("=============================", flush=True)
            print("开始上传"+ str(room_id), flush=True)
            print("=============================", flush=True)
        else:
            logging.warning(f"upload: Room {room_id} not found in upload list{cls._upload_list}")
        
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
        cls.room_ids[room_id] = live.dump(path = MyHandler._video_list_directory)
    
    @classmethod
    def handle_recording_finished(cls, event:dict):
        room_id = event['data']['room_info']['room_id']
        try:
            list_file = cls.room_ids.pop(room_id)
            
            if list_file in cls.videos_active.values():
                cls.lists_fin_wait.add(list_file)
            else:
                cls.finalize_list(list_file)

        except Exception as e:
            logging.exception(e)

    @classmethod
    def finalize_list(cls, list_file):
        live = Live(filename = list_file)
        live.update_live_status("Done")
        live.dump()
        logging.warning(f"Video list '{list_file}' is finished.")        
        
    @classmethod
    def handle_room_change(cls, event:dict):
        room_id = event['data']['room_info']['room_id']

        if room_id in cls.room_ids:
            live = Live(filename = cls.room_ids[room_id])
            live.update_live_title_now(event['data']['room_info']['title'])
            live.dump()
        else:
            logging.warning(f"handle_room_change: Room {room_id} not found in data store")
    
    @classmethod
    def handle_video_create(cls, event:dict):
        room_id = event['data']['room_id']
        filename = event['data']['path']

        if room_id in cls.room_ids:
            live = Live(filename = cls.room_ids[room_id])
            live.add_video_now_v1(
                    start_time = event['date'],
                    filename = filename
                    )
            list_file = live.dump()
            cls.videos_active[filename] = list_file
        else:
            logging.warning(f"handle_video_create: Room {room_id} not found in data store")

    @classmethod
    def handle_video_file_completed(cls, event:dict):
        filename = event['data']['path']
        list_file = cls.videos_active.pop(filename)
        
        live = Live(filename = list_file)
        live.finalize_video_v1(
                filename = filename
                )
        live.dump()

    
        if list_file in cls.lists_fin_wait:
            if list_file not in cls.videos_active.values():
                cls.finalize_list(list_file)
                cls.lists_fin_wait.remove(list_file)
            

    @classmethod
    def shutdown(cls):
        for room_id in cls.room_ids:
            live = Live(filename = cls.room_ids[room_id])
            live.update_live_status("Done")
            live.dump()
        for list_file in cls.lists_fin_wait:
            live = Live(filename = list_file)
            live.update_live_status("Done")
            live.dump()

