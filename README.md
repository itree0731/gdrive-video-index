# Google Drive 视频索引（Grok Bot 云电脑）

仅索引 Google Drive 指定文件夹及子目录里的视频元数据，不播放、不下载、不代理视频，也不开放入站端口。

## 安装

1. 在 [Google Cloud Console](https://console.cloud.google.com/) 启用 Google Drive API，创建服务账号并下载 JSON 密钥。把要扫描的文件夹共享给该服务账号（查看者）。**不要将密钥上传到 GitHub。**
2. 将本仓库克隆到 Grok Bot 云电脑，并安装依赖：

```bash
git clone https://github.com/itree0731/gdrive-video-index.git
cd gdrive-video-index
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

3. 在云电脑安全地放置服务账号 JSON，并配置环境变量：

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/workspace/private/gdrive-reader.json
export GDRIVE_FOLDER_ID='你的网盘文件夹ID'
python drive_video_index.py scan
python drive_video_index.py search '三体'
python drive_video_index.py link '搜索所得文件ID' --json
```

请勿把凭据写入仓库或粘贴到聊天中。目录 ID 从 Google Drive 文件夹 URL 获取。

## 返回链接的区别

- `browser_view_url`：网盘预览页面；
- `browser_download_url`：Google 官方网页下载地址，可能要求登录、Cookie、确认；
- `api_download_url`：原始文件下载 API，私有文件必须携带 `Authorization: Bearer ACCESS_TOKEN`；**不是匿名永久直链**。

`scan` 联网更新本地 `catalog.json`；`search` 和 `link` 仅读取索引。休眠后可读取保留的索引，但云电脑不保证长期在线。快捷方式目标不会被递归追踪。

Google Drive API 文档：https://developers.google.com/workspace/drive/api/guides/search-files
