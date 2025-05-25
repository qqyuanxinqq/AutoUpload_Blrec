import time, datetime
import os
import json


from .api import download_file

def burn_subtitle_jsonl(video_file_path, embed_emoticon = 1):
    (root, ext) = os.path.splitext(video_file_path)
    jsonl_file = root + ".jsonl"
    if not os.path.exists(jsonl_file):
        print(f"jsonl file {jsonl_file} not found.")
        return

    jsonl_ass_generator = Ass_Generator(jsonl_file, embed_emoticon = embed_emoticon)

    try:
        jsonl_ass_generator.process()
        jsonl_ass_generator.embed(video_file_path)
    except Exception as e:
        print(f"Exception occurred: {e}")
        

def embed_subtitles(ass_file, video_file_path, timeout = 600, overlays_script = None):
    """
    Use ffmpeg to burn substitles into the video. 
    Redirect video_db to the subtitled_video, and delete the unsubtitled one. 
    """
    start = time.perf_counter() 
    if not os.path.exists(ass_file):
        print(f"ass_file {ass_file} not found.")
        return

    import subprocess
    process = subprocess.run(['ffmpeg', '-version'], stdout= subprocess.PIPE)
    if process.returncode:
        raise FileNotFoundError("FFmpeg not found. FFmpeg must be installed and accessible via the $PATH environment variable")

    subtitledVideo = ".".join(video_file_path.split(".")[:-1]) + "_subtitled.flv"
    print(f'starting FFmpeg embedding subtitle  \n{ass_file}\n {"with" if overlays_script else "without"} emoticons, to:\n{video_file_path}\n and output to \n{subtitledVideo}', datetime.datetime.now())

    if overlays_script:
        cmd = ['ffmpeg', 
            '-loglevel', 'warning', 
            '-vcodec', 'h264_cuvid', 
            '-i', video_file_path, 
            '-filter_complex_script', overlays_script,
            '-map', '[out]',    #[out] should be defined in the overlays_script
            '-acodec', 'copy', 
            '-cq', '30', 
            '-flvflags', 
            'add_keyframe_index', 
            '-map', '0:a', 
            '-vcodec', 'h264_nvenc', 
            subtitledVideo, 
            '-y']
    else:
        cmd = ['ffmpeg', 
           '-loglevel', 'warning', 
           '-vcodec', 'h264_cuvid', 
           '-i', video_file_path, 
           '-filter_complex', f'[0]ass={ass_file}[s0]', 
           '-map', '[s0]', 
           '-acodec', 'copy', 
           '-cq', '30', 
           '-flvflags', 
           'add_keyframe_index', 
           '-map', '0:a', 
           '-vcodec', 'h264_nvenc', 
           subtitledVideo, 
           '-y']
    
    run: subprocess.Popen = subprocess.Popen(cmd)

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

    end = time.perf_counter()
    print(f"Elapsed: {end - start:.6f} seconds")

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

def get_url_extension(url):
    filename = url.split('/')[-1]
    if '.' in filename:
        return filename.rsplit('.', 1)[-1]
    return ''

class Emoticon():
    def __init__(self, start_time, end_time, Y, emoticon_file):
        self.start_time = start_time
        self.end_time = end_time
        self.Y = Y
        self.emoticon_file = emoticon_file

class Ass_Generator():
    """
    Generate and write danmu to *.ass file
    """
    ASS_DURATION = 10
    RES_X = 1920
    RES_Y = 1080
    FONT = 37.5
    EMOTICON_HEIGHT = 1.8 #Multiplier of font size
    EMOTICON_SIZE = EMOTICON_HEIGHT*FONT

    def __init__(self, jsonl_file, embed_emoticon = 1) -> None:
        self.jsonl = jsonl_file
        self.embed_emoticon = embed_emoticon # If set 1, embed emoticon image into the video, requires network connected.
        self.danmu_end_time = []
        self.SC_end_time = []
            
        (root, ext) = os.path.splitext(jsonl_file)
        self.ass_file = root + ".ass"
        self.ass_lines = []

        self.emoticon_dir = os.path.join(os.path.dirname(jsonl_file), "emoticon")
        self.ffmpeg_script = root+"_ffmpeg_script.txt"
        self.emoticons = dict() #
        
        

        video_datetime_str = os.path.basename(root).split("_")[1].replace("-", ":")
        self.video_start_time = datetime.datetime.strptime(video_datetime_str, "%Y%m%d:%H:%M:%S")

        return
   
    def process(self):
        if self.embed_emoticon == 1:
            if not os.path.exists(self.emoticon_dir):
                os.makedirs(self.emoticon_dir)
            self.emoticon_files = set(
                os.path.abspath(os.path.join(self.emoticon_dir, f)) for f in os.listdir(self.emoticon_dir)
            )

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
        
        # self.emoticons contains all the info of appearance for each emoticon.
        # Output a ffmpeg script to output overlays that animate the emoticons (horizontally, at different Ys)
        script_lines = [f"[0:v]ass={self.ass_file}[s0]"]
        tmp_tag = "[s0]"
        for i, (emoticon_file, items) in enumerate(self.emoticons.items()):
            # Scale the emoticon image to EMOTICON_SIZE
            script_lines.append(f"movie={emoticon_file}:loop=1,scale={int(self.EMOTICON_SIZE)}:-1[img{i}]")  #test
            script_lines.append(f"[img{i}]split={len(items)}" + "".join([f"[img{i}_{j}]" for j in range(len(items))]))
            for j, emoticon in enumerate(items):
                overlay_tag = f"[tmp{i}_{j}]"
                enable_expr = f"between(t,{emoticon.start_time},{emoticon.end_time})"
                script_lines.append(
                    f"{tmp_tag}[img{i}_{j}]overlay=x='W-(W+w)*(t-{emoticon.start_time})/10':y={emoticon.Y}:enable='{enable_expr}'{overlay_tag}"
                )
                tmp_tag = overlay_tag
        script_lines.append(f"{tmp_tag}null[out]")
        # Output ffmpeg script as text
        script_text = ";\n".join(script_lines)
        with open(self.ffmpeg_script,"w",encoding='UTF-8') as f:
            f.write(script_text)  
        return 
    


    def embed(self, video_file_path):
        if self.embed_emoticon == 1:
            embed_subtitles(self.ass_file, video_file_path, overlays_script = self.ffmpeg_script)
        else:
            embed_subtitles(self.ass_file, video_file_path)

    def handle(self, j):
        message_type = j.get("cmd")
        if message_type == "DANMU_MSG":
            if j.get('info')[1] in BLACK_LIST:
                return
            if self.embed_emoticon == 0:
                ass_line = self._danmu_to_ass_line(j, self.danmu_end_time, self.video_start_time)
                self.ass_lines.append(ass_line)

            if self.embed_emoticon == 1:
                if j.get('info')[0][12] == 1:
                # if j.get('info')[0][13] != "{}":
                    self._emoticon_process(j, self.danmu_end_time, self.video_start_time)
                else:
                    ass_line = self._danmu_to_ass_line(j, self.danmu_end_time, self.video_start_time)
                    self.ass_lines.append(ass_line)
                    return

        if message_type == "SUPER_CHAT_MESSAGE":
            ass_line = self._SC_to_ass_line(j, self.SC_end_time, self.video_start_time)
            self.ass_lines.append(ass_line)

    def _SC_to_ass_line(self, j, end_time_lst, starttime):
        username = j["data"]["user_info"]["uname"]
        color_h= j["data"]["background_bottom_color"][1:7]          #RGB in Hexadecimal
        price = j["data"]["price"]
        timestamp_start = j["data"]["start_time"]
        timestamp_end = j["data"]["end_time"]
        danmu = f"SC({price}) {username}: "+j["data"]["message"]


        danmu_l=len(danmu)*self.FONT
        danmu_start = datetime.datetime.fromtimestamp(timestamp_start)-starttime
        danmu_end = datetime.datetime.fromtimestamp(timestamp_end)-starttime
        #Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        #Moving danmu: \move(<Start_x1>,<Start_y1>,<End_x2>,<End_y2>)
        Y = 0
        for i in range(len(end_time_lst)+1):
            if i == len(end_time_lst):
                Y=i*self.FONT
                end_time_lst.append(danmu_end + danmu_l/self.RES_X*self.ASS_DURATION*datetime.timedelta(seconds=1))
                break
            if (self.RES_X + danmu_l) / self.ASS_DURATION * ((end_time_lst[i] - danmu_start)/datetime.timedelta(seconds=1)) >  self.RES_X: 
                continue
            else:
                Y=i*self.FONT
                end_time_lst[i] = danmu_end + danmu_l/self.RES_X*self.ASS_DURATION*datetime.timedelta(seconds=1)
                break
        move = "\\pos({},{})".format(self.RES_X//2, self.RES_Y - self.FONT - Y)+"\\c&H{}".format(''.join([color_h[4:6],color_h[2:4],color_h[0:2]]))
        ass_line="Dialogue: 0,{},{},R2L,{},20,20,2,,{{ {} }}{} \n".format(ass_time(danmu_start), 
                                                        ass_time(danmu_end),
                                                        username,
                                                        move,
                                                        danmu)
        return ass_line


    def _emoticon_process(self, j, end_time_lst, starttime):
        emoticon_info = j.get('info')[0][13]

        #input of ffmpeg script should not contain "[" or "]"
        basename = emoticon_info["emoticon_unique"].replace("[", "").replace("]", "")
        emoticon_file = basename + "." + get_url_extension(emoticon_info["url"])
        emoticon_file = os.path.join(self.emoticon_dir,emoticon_file)
        # 确保emoticon_file为绝对路径，避免路径混淆
        emoticon_file = os.path.abspath(emoticon_file)
        if emoticon_file not in self.emoticon_files:
            download_file(emoticon_info["url"], emoticon_file)
            self.emoticon_files.add(emoticon_file)


        danmu_start = datetime.datetime.fromtimestamp(j.get('info')[0][4]/1000)-starttime
        danmu_l=self.EMOTICON_SIZE
        danmu_end = danmu_start + datetime.timedelta(seconds=self.ASS_DURATION)
        
        #Place holder in ass list.
        Y = 0
        for i in range(len(end_time_lst)+1):
            if i == len(end_time_lst):
                Y=i*self.FONT
                end_time_lst.append(danmu_end + danmu_l/self.RES_X*self.ASS_DURATION*datetime.timedelta(seconds=1))
                end_time_lst.append(danmu_end + danmu_l/self.RES_X*self.ASS_DURATION*datetime.timedelta(seconds=1))
                break
            if (self.RES_X + danmu_l) / self.ASS_DURATION * ((end_time_lst[i] - danmu_start)/datetime.timedelta(seconds=1)) <=  self.RES_X: 
                if i+1 == len(end_time_lst):
                    Y=i*self.FONT
                    end_time_lst[i] = danmu_end + danmu_l/self.RES_X*self.ASS_DURATION*datetime.timedelta(seconds=1)
                    end_time_lst.append(danmu_end + danmu_l/self.RES_X*self.ASS_DURATION*datetime.timedelta(seconds=1))
                    break
                if (self.RES_X + danmu_l) / self.ASS_DURATION * ((end_time_lst[i+1] - danmu_start)/datetime.timedelta(seconds=1)) <=  self.RES_X:
                    Y=i*self.FONT
                    end_time_lst[i] = danmu_end + danmu_l/self.RES_X*self.ASS_DURATION*datetime.timedelta(seconds=1)
                    end_time_lst[i+1] = danmu_end + danmu_l/self.RES_X*self.ASS_DURATION*datetime.timedelta(seconds=1)
                    break
        # Convert both danmu_start and danmu_end to seconds
        danmu_start = danmu_start.total_seconds()
        danmu_end = danmu_end.total_seconds()
        
        item = Emoticon(danmu_start, danmu_end, Y, emoticon_file)
        if emoticon_file not in self.emoticons:
            self.emoticons[emoticon_file] = [item]
        else:
            self.emoticons[emoticon_file].append(item)

    def _danmu_to_ass_line(self, j, end_time_lst, starttime):
        """Input json object and parameters for single msg, output string in ass format"""
        danmu = j.get('info')[1]
        username = j.get('info')[2][1]
        color_d=j.get('info')[0][3] #RGB in decimal
        color_h="{:X}".format(color_d) #RGB in Hexadecimal
        danmu_start = datetime.datetime.fromtimestamp(j.get('info')[0][4]/1000)-starttime
        
        danmu_l=len(danmu)*self.FONT   #Size of each chinese character is 25, english character considered to be half, 1280 is the X size from the .ass file
        danmu_end = danmu_start + datetime.timedelta(seconds=self.ASS_DURATION)
        #Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
        #Moving danmu: \move(<Start_x1>,<Start_y1>,<End_x2>,<End_y2>)
        X1 = self.RES_X + danmu_l / 2
        X2 = 0 - danmu_l / 2
        Y = 0
        for i in range(len(end_time_lst)+1):
            if i == len(end_time_lst):
                Y=i*self.FONT
                end_time_lst.append(danmu_end + danmu_l/self.RES_X*self.ASS_DURATION*datetime.timedelta(seconds=1))
                break
            if (self.RES_X + danmu_l) / self.ASS_DURATION * ((end_time_lst[i] - danmu_start)/datetime.timedelta(seconds=1)) <=  self.RES_X: 
                Y=i*self.FONT
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
Style: Fix,Microsoft YaHei UI,{self.FONT},&H00FFFFFF,&H00FFFFFF,&H00000000,&H66000000,1,0,0,0,100,100,0,0,1,1,0,8,20,20,2,0
Style: R2L,Microsoft YaHei UI,{self.FONT},&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,1,0,8,20,20,2,0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
        with open(ass_file,"w",encoding='UTF-8') as f_ass:
            f_ass.write(ass_head)  

# jsonl_ass_generator = Ass_Generator("22259479_20250520-16-20-55.jsonl")
# jsonl_ass_generator = Ass_Generator("22259479_20250520-14-30-04.jsonl")
# ass_file = jsonl_ass_generator.process()
# jsonl_ass_generator.embed("input.flv")


# embed_subtitles("/home/xyl/f/blive/Videos/22259479/22259479_20250520-04-30-42.ass","/home/xyl/f/blive/Videos/22259479/22259479_20250520-04-30-42.flv", overlays_script = "/home/xyl/f/blive/Videos/22259479/22259479_20250520-04-30-42_ffmpeg_script_optimized_fixed.txt")
# burn_subtitle_jsonl("/home/xyl/f/blive/Videos/22259479/22259479_20250520-04-30-42.flv", embed_emoticon = 1)