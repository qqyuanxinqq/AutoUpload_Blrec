import json
import os
from datetime import datetime
import collections

from filelock import FileLock
class Live():
    '''
    Provide the mapping between python dictionary and json object save in files. 
    '''
    def __init__(self, filename = None):
        if filename is not None:
            with open(filename, 'r', encoding='utf-8') as f:
                self._data = json.load(f)
        else:
            self._data = {}

        self.filename = filename

    def create_v1(
            self,
            room_id:str,
            start_time:str,
            live_title:str,
            status = "Done",
            is_uploaded = False,
            version = "v1",
            ):
        
        timestamp_dt = datetime.fromisoformat(start_time)
        self._data = {
            "version": version,
            "room_id": str(room_id),
            "time": start_time, # ISO time format
            "year": timestamp_dt.strftime("%Y"),
            "month": timestamp_dt.strftime("%m"),
            "day": timestamp_dt.strftime("%d"),
            "hour": timestamp_dt.strftime("%H"),
            "minute": timestamp_dt.strftime("%M"),
            "second": timestamp_dt.strftime("%S"),
            "live_title": live_title,
            "status": status,
            "is_uploaded": is_uploaded,
            "video_list": []
        }

    def add_video_v1(
            self,
            start_time:str,
            filename:str
            ):
        
        self._data['video_list'].append({
            "start_time": start_time, # ISO time format
            "filename": filename,
            "live_title": self._data["live_title"]
        })

    def update_live_title(self, live_title:str):
        self._data["live_title"] = live_title

    def update_live_status(self, status:str):
        self._data["status"] = status


    def dump(self, filename = None, path = ""):
        """
        Dump the data to the file.
        """
        if filename is None:
            if self.filename is not None:
                filename = self.filename
            else:
                timestamp = datetime.fromisoformat(self._data['time']).strftime("_%Y%m%d_%H-%M-%S")
                self.filename = os.path.join(path, f"{self._data['room_id']}{timestamp}.json")
                filename = self.filename

        with FileLock(f"{filename}.lock"):
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, indent=4)
        return filename

    def load(self, filename):
        """
        Load the data from the file.
        """
        with FileLock(f"{filename}.lock"):
            with open(filename, 'r', encoding='utf-8') as f:
                self._data = json.load(f)

    def islive(self):
        if self._data["version"] == "v1":
            return self._data["status"] == "Living"
        
    def update_server_name(self, filename:str, server_name:str):
        """
        Find the dictionary in video_list with filename, and update the server_name.
        """
        for item in self._data["video_list"]:
            if item["filename"] == filename:
                item["server_name"] = server_name
                break



data = {
    "version": "v1",
    "time_format": "_%Y%m%d_%H-%M-%S",
    "live_DB": {
        "nickname": "kaofish",
        "room_id": 22259479,
        "live_title": "\ud83d\udc1f\u7ec8\u5c06\u6210\u4e3a\u672f\ud83d\udc1f",
        "start_time": 1696315449,
        "live_id": 306,
        "is_uploaded": False,
        "end_time": 1696315487
    },
    "year": "2023",
    "month": "10",
    "day": "03",
    "hour": "14",
    "up_name": "kaofish",
    "live_title": "\ud83d\udc1f\u7ec8\u5c06\u6210\u4e3a\u672f\ud83d\udc1f",
    "status": "Done",
    "video_list": [
        {
            "start_time": 1696315467,
            "video_basename": "kaofish_20231003_14-44-27.flv",
            "video_directory": "Videos/kaofish",
            "subtitle_file": "Videos/kaofish/kaofish_20231003_14-44-27.ass",
            "is_live": False,
            "is_stored": True,
            "live_title": "\ud83d\udc1f\u7ec8\u5c06\u6210\u4e3a\u672f\ud83d\udc1f",
            "end_time": 1696315486,
            "duration": 19,
            "size": 23691264,
            "deletion_type": 2,
            "live_id": 306,
            "video_id": 4472
        }
    ]
}

