from http.server import BaseHTTPRequestHandler
import json
import logging
import os

from .Live import Live
from .Myproc import Myproc

from .blive_upload import configured_upload
from .api import get_title
from .danmu import burn_subtitle_jsonl

class MyHandler(BaseHTTPRequestHandler):

    # dict room_id(int): list_file path
    room_ids = {}
    # dict active video_file path (not full path, root only, without extension): list_file path
    videos_active = {}
    # set of list_file path for each list_file that is waiting for all videos to be finalized
    lists_fin_wait = set()
    
    _video_list_directory = ""
    _upload_log_dir = ""
    _upload_list = []   #str
    _danmu_embed_list = []  #str
    
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

    @classmethod
    def set_danmu_embed_list(cls):
        with open("upload_config.json", 'r', encoding='utf-8') as f:
            config = json.load(f)
        temp = []
        for key, value in config.items():
            if value.get("danmu_embedding"):
                temp.append(key)
        cls._danmu_embed_list = temp


    def do_POST(self):
        # You might want to send a response back to the client
        # Here, we send a simple "OK" text.
        self.send_response_only(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'OK')

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        try:
            # Deserialize the JSON payload
            event = json.loads(post_data)
            self.log_event(event)
            self.handle_event(event)

        except Exception as e:
            logging.exception(e)

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
            MyHandler.set_danmu_embed_list()
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
        """
        Create a new video list file, and add dumped filename to room_ids.
        """
        live = Live()
        room_id = event['data']['room_info']['room_id']
        
        title = get_title(room_id)
        if title is None:
            title = event['data']['room_info']['title']

        live.create_v1(
                room_id = room_id,
                start_time = event['date'],
                live_title = title,
                status="Living"
                )
        cls.room_ids[room_id] = live.dump(path = MyHandler._video_list_directory)
    
    @classmethod
    def handle_recording_finished(cls, event:dict):
        """
        Pop the video list file from room_ids. 
        Put it into lists_fin_wait if there is video active, otherwise finalize it.
        """
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
        """
        Finalize the video list file, set status to Done.
        """
        live = Live(filename = list_file)
        live.update_live_status("Done")
        live.dump()
        logging.warning(f"Video list '{list_file}' is finished.")        
        
    @classmethod
    def handle_room_change(cls, event:dict):
        room_id = event['data']['room_info']['room_id']

        title = get_title(room_id)
        if title is None:
            title = event['data']['room_info']['title']

        if room_id in cls.room_ids:
            live = Live(filename = cls.room_ids[room_id])
            live.update_live_title_now(title)
            live.dump()
        else:
            logging.warning(f"handle_room_change: Room {room_id} not found in data store")
    
    @classmethod
    def handle_video_create(cls, event:dict):
        room_id = event['data']['room_id']
        filename = event['data']['path']

        title = get_title(room_id)

        if room_id in cls.room_ids:
            live = Live(filename = cls.room_ids[room_id])
            if title is not None:
                live.update_live_title_now(title)
            
            live.add_video_now_v1(
                    start_time = event['date'],
                    filename = filename
                    )
            list_file = live.dump()
            (root, ext) = os.path.splitext(filename)
            cls.videos_active[root] = list_file
        else:
            logging.warning(f"handle_video_create: Room {room_id} not found in data store")

    @classmethod
    def handle_video_file_completed(cls, event:dict):
        """
        Finalize the video file, and remove it from videos_active.
        Then check if the paraent list is in lists_fin_wait, finalize it if no more video in the list is active.
        """
        filename = event['data']['path']
        (root, ext) = os.path.splitext(filename)
        list_file = cls.videos_active.pop(root)
        
        live = Live(filename = list_file)

        if int(live._data['room_id']) in cls.room_ids:
            if str(live._data['room_id']) in cls._danmu_embed_list:
                burn_subtitle_jsonl(filename)

        # if this is the first video file, update live_title and video title
        # This because the lag in title updating from bilibili API
        if len(live._data['video_list']) == 0:
            title = get_title(live._data['room_id'])
            if title is not None:
                live.update_live_title(title)
                live.update_live_title_now(title)
                live.finalize_video_v1(filename = filename, title = title)
        else:
            live.finalize_video_v1(filename = filename)

        live.dump()

        # if the list is in lists_fin_wait fin_wait, finalize it if no video is active
        if list_file in cls.lists_fin_wait:
            if list_file not in cls.videos_active.values():
                cls.finalize_list(list_file)
                cls.lists_fin_wait.remove(list_file)
            

    @classmethod
    def shutdown(cls):
        """
        Set status of all video list files to Done.
        """
        for room_id in cls.room_ids:
            live = Live(filename = cls.room_ids[room_id])
            live.update_live_status("Done")
            live.dump()
        for list_file in cls.lists_fin_wait:
            live = Live(filename = list_file)
            live.update_live_status("Done")
            live.dump()

