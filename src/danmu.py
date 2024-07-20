import time, datetime
import os
import json

def burn_subtitle_jsonl(video_file_path):
    (root, ext) = os.path.splitext(video_file_path)
    jsonl_file = root + ".jsonl"
    if not os.path.exists(jsonl_file):
        print(f"jsonl file {jsonl_file} not found.")
        return

    jsonl_ass_generator = Ass_Generator(jsonl_file)
    ass_file = jsonl_ass_generator.process()
    try:
        embed_subtitles(ass_file, video_file_path)
    except Exception as e:
        print(f"Exception occurred: {e}")
        

def embed_subtitles(ass_file, video_file_path, timeout = 600):
    """
    Use ffmpeg to burn substitles into the video. 
    Redirect video_db to the subtitled_video, and delete the unsubtitled one. 
    """

    if not os.path.exists(ass_file):
        print(f"ass_file {ass_file} not found.")
        return

    import subprocess
    process = subprocess.run(['ffmpeg', '-version'], stdout= subprocess.PIPE)
    if process.returncode:
        raise FileNotFoundError("FFmpeg not found. FFmpeg must be installed and accessible via the $PATH environment variable")

    subtitledVideo = ".".join(video_file_path.split(".")[:-1]) + "_subtitled.flv"
    print(f'starting FFmpeg embedding subtitle \n{ass_file}\nto:\n{video_file_path}\n and output to \n{subtitledVideo}', datetime.datetime.now())
    
    import ffmpeg
    run: subprocess.Popen = (ffmpeg.input(
        video_file_path,
        vcodec="h264_cuvid",  # GPU accelerated
        loglevel = "warning",
    )
        .filter("ass", ass_file)
        .output(
            subtitledVideo,
            vcodec="h264_nvenc",  # GPU accelerated
            acodec="copy",
            map="0:a",  # Map audio channel
            cq="30",  # Lower number means better quality and larger size
            flvflags = "add_keyframe_index"     #Used to facilitate seeking
        )
        .overwrite_output()          #Overwrite output files without asking (ffmpeg -y option)
        .run_async()
    )

    #Check whether the size of output is changing.
    size = 0 
    delta_t = 10
    try:
        prev_size = 0
        while True:
            time.sleep(delta_t)
            size = 0 if not os.path.isfile(subtitledVideo) else os.path.getsize(subtitledVideo)

            if run.poll() is None:
                if size == prev_size:
                    timeout = timeout - delta_t
                    if timeout <= 0:
                        print("=============embed_subtitle not working somehow!==============")
                        break
            else:
                print(f"============={subtitledVideo} finisheded!==============",flush=True)
                break
            prev_size = size
    finally:
        run.terminate()

    #Update video_db info
    rtncode = run.poll()
    if not os.path.isfile(subtitledVideo) or rtncode != 0:
        if os.path.isfile(subtitledVideo):
            os.remove(subtitledVideo)
        raise Exception(f"burn_subtitle failed, error code {rtncode}")
    else:
        os.remove(video_file_path)
        print(f"os.remove({video_file_path})",flush=True)
        os.rename(subtitledVideo, video_file_path) #Rename the subtitled video to the original name
        print(f"os.rename({subtitledVideo}, {video_file_path})",flush=True)
        # os.remove(video_db.subtitle_file)
        # video_db.subtitle_file = ""

BLACK_LIST=[
    "老板大气！点点红包抽礼物！",
    "赞",
    "老板大气！点点红包抽礼物",
    "喜欢主播加关注，点点红包抽礼物",
    "点点红包，关注主播抽礼物～"
    ]

def ass_time(timedelta):    
    """input 'datetime.timedelta' object, return ass time formt in str"""
    h=(timedelta//datetime.timedelta(seconds=3600))%10
    m=(timedelta//datetime.timedelta(seconds=60))%60
    s=(timedelta//datetime.timedelta(seconds=1))%60
    sd=(timedelta//datetime.timedelta(microseconds=10**4))%100
    return "{}:{:0>2d}:{:0>2d}.{:0>2d}".format(h,m,s,sd)

class Ass_Generator():
    """
    Generate and write danmu to *.ass file
    """
    ASS_DURATION = 10
    RES_X = 1280
    RES_Y = 720

    def __init__(self, jsonl_file) -> None:
        self.jsonl = jsonl_file
        self.danmu_end_time = []
    
        (root, ext) = os.path.splitext(jsonl_file)
        self.ass_file = root + ".ass"

        video_datetime_str = os.path.basename(root).split("_")[1].replace("-", ":")
        self.video_start_time = datetime.datetime.strptime(video_datetime_str, "%Y%m%d:%H:%M:%S")

        self.ass_lines = []
        return
   
    def process(self):
        with open(self.jsonl, "r") as f:
            for line in f:
                j = json.loads(line)
                self.handle(j)
                # process the json object
                # call danmu_handler or SC_handler with the json object

        self.ass_gen(self.ass_file)
        with open(self.ass_file,"a",encoding='UTF-8') as f:
            for ass_line in self.ass_lines:
                f.write(ass_line)
        print(f"Total {len(self.ass_lines)} lines have been written.")
        return self.ass_file

    def handle(self, j):
        message_type = j.get("cmd")

        if message_type == "DANMU_MSG":
            if j.get('info')[1] in BLACK_LIST:
                return
            else:
                ass_line = self._danmu_to_ass_line(j, self.danmu_end_time, self.video_start_time)
                self.ass_lines.append(ass_line)
        if message_type == "SUPER_CHAT_MESSAGE":
            ass_line = self._SC_to_ass_line(j, self.danmu_end_time, self.video_start_time)
            self.ass_lines.append(ass_line)

    def _SC_to_ass_line(self, j, end_time_lst, starttime):
        danmu = "SC:"+j["data"]["message"]
        username = j["data"]["user_info"]["uname"]
        color_h= j["data"]["background_bottom_color"][1:7]          #RGB in Hexadecimal
        timestamp_start = j["data"]["start_time"]
        timestamp_end = j["data"]["end_time"]

        danmu_l=len(danmu)*25
        danmu_start = datetime.datetime.fromtimestamp(timestamp_start)-starttime
        danmu_end = datetime.datetime.fromtimestamp(timestamp_end)-starttime
        #Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        #Moving danmu: \move(<Start_x1>,<Start_y1>,<End_x2>,<End_y2>)
        Y = 0
        for i in range(len(end_time_lst)+1):
            #print(i)
            if i == len(end_time_lst):
                Y=i*25
                end_time_lst.append(danmu_end + danmu_l/self.RES_X*self.ASS_DURATION*datetime.timedelta(seconds=1))
                break
            if (self.RES_X + danmu_l) / self.ASS_DURATION * ((end_time_lst[i] - danmu_start)/datetime.timedelta(seconds=1)) >  self.RES_X: 
                continue
            else:
                Y=i*25
                end_time_lst[i] = danmu_end + danmu_l/self.RES_X*self.ASS_DURATION*datetime.timedelta(seconds=1)
                break
        move = "\\pos({},{})".format(self.RES_X//2, Y)+"\\c&H{}".format(''.join([color_h[4:6],color_h[2:4],color_h[0:2]]))
        ass_line="Dialogue: 0,{},{},R2L,{},20,20,2,,{{ {} }}{} \n".format(ass_time(danmu_start), 
                                                        ass_time(danmu_end),
                                                        username,
                                                        move,
                                                        danmu)
        return ass_line

    def _danmu_to_ass_line(self, j, end_time_lst, starttime):
        """Input json object and parameters for single msg, output string in ass format"""
        danmu = j.get('info')[1]
        username = j.get('info')[2][1]
        color_d=j.get('info')[0][3] #RGB in decimal
        color_h="{:X}".format(color_d) #RGB in Hexadecimal
        danmu_start = datetime.datetime.fromtimestamp(j.get('info')[0][4]/1000)-starttime
        
        danmu_l=len(danmu)*25   #Size of each chinese character is 25, english character considered to be half, 1280 is the X size from the .ass file
        danmu_end = danmu_start + datetime.timedelta(seconds=self.ASS_DURATION)
        #Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        #Moving danmu: \move(<Start_x1>,<Start_y1>,<End_x2>,<End_y2>)
        X1 = self.RES_X + danmu_l / 2
        X2 = 0 - danmu_l / 2
        Y = 0
        for i in range(len(end_time_lst)+1):
            #print(i)
            if i == len(end_time_lst):
                Y=i*25
                end_time_lst.append(danmu_end + danmu_l/self.RES_X*self.ASS_DURATION*datetime.timedelta(seconds=1))
                break
            if (self.RES_X + danmu_l) / self.ASS_DURATION * ((end_time_lst[i] - danmu_start)/datetime.timedelta(seconds=1)) <=  1280: 
                Y=i*25
                end_time_lst[i] = danmu_end + danmu_l/self.RES_X*self.ASS_DURATION*datetime.timedelta(seconds=1)
                break
        move = "\\move({},{},{},{})".format(X1, Y, X2, Y)+"\\c&H{}".format(''.join([color_h[4:6],color_h[2:4],color_h[0:2]]))
        ass_line="Dialogue: 0,{},{},R2L,{},20,20,2,,{{ {} }}{} \n".format(ass_time(danmu_start), 
                                                        ass_time(danmu_end),
                                                        username,
                                                        move,
                                                        danmu)
        return ass_line

    def ass_gen(self, ass_file):

        ass_head =f'''\
[Script Info]
Title: blive_Recorder danmu generator
ScriptType: v4.00+
Collisions: Normal
PlayResX: {self.RES_X}
PlayResY: {self.RES_Y}
Timer: 10.0000

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Fix,Microsoft YaHei UI,25,&H00FFFFFF,&H00FFFFFF,&H00000000,&H66000000,1,0,0,0,100,100,0,0,1,1,0,8,20,20,2,0
Style: R2L,Microsoft YaHei UI,25,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,1,0,8,20,20,2,0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
        with open(ass_file,"w",encoding='UTF-8') as f_ass:
            f_ass.write(ass_head)  
