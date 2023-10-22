# 基于blrec webhook 的自动投稿工具

用于B站的，全自动录制（含弹幕）、自动投稿命令行工具。

**适用于：NAS、服务器直播监控、录制及自动投稿，适配Windows 和 linux**

- 录制、上传同步进行，下播前就能发布录播，再长的直播也能结束后半小时内全部上传。快就是快！
- 自定义投稿描述，支持格式化的直播间信息
- 后台24小时监视直播间，自动启用录制和投稿
- 支持多P上传。支持单一视频的多线程上传
- 一键启动

## 基本结构
[blrec](https://github.com/acgnhiki/blrec)录播，基于其webhook事件触发视频目录编写以及投稿进程。

投稿进程读取动态更新的视频目录进行上传、投稿。

### 环境
建议Python3.10+, 3.10以下未测试
```
pip install -r requirements.txt
```

### 运行
- Windows, 在配置好的Python环境中运行`run.bat`

blrec 和 自动投稿程序 会分别在两个跳出的命令行窗口中运行
```
run.bat
```


- Linux, 在配置好的Python环境中运行`run.sh`

blrec 和 自动投稿程序 会自动在后台运行
```bash
bash ./run.sh
```
### 配置
#### blrec
- 在`run.sh`或`run.bat`启动脚本中设置端口`port`
- 在`settings.toml`中设置视频存放目录、日志目录，可使用绝对路径
- 打开`http://localhost:port`进入blrec前端界面进行设置
- blrec具体配置文件为`settings.toml`，详见 [blrec](https://github.com/acgnhiki/blrec)

#### 自动投稿
- 投稿的配置文件为`upload_config.json`
- 请在将一级键值名称取为**字符串格式**的对应直播间的长房间号
  - 非短号，如1220无效，应为12962。
- 于B站登录接口限制，请使用[biliup-rs](https://github.com/biliup/biliup-rs)登录：
  - 将 biliup-rs 登录产生的`cookies.json`文件放在 `login_token_file`所指的位置
- 支持配置文件的“热修改”，在下次投稿时起效

## 参考及感谢

- [FortuneDayssss/BilibiliUploader](https://github.com/FortuneDayssss/BilibiliUploader) 上传和投稿部分基于该项目
- [acgnhiki/blrec](https://github.com/acgnhiki/blrec)
- [biliup/biliup-rs](https://github.com/biliup/biliup-rs)






