#!/usr/bin/env python3
"""Index Google Drive videos without downloading or proxying content."""
import argparse
import json
import os
from collections import deque
from pathlib import Path
from urllib.parse import quote

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

API = "https://www.googleapis.com/drive/v3/files"
FOLDER = "application/vnd.google-apps.folder"
SHORTCUT = "application/vnd.google-apps.shortcut"
EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".wmv", ".flv", ".ts", ".mpg", ".mpeg", ".3gp"}
DB = Path(__file__).with_name("catalog.json")
FIELDS = "nextPageToken,files(id,name,mimeType,size,webViewLink,webContentLink,capabilities(canDownload))"

def request(session, url, **kwargs):
    r = session.get(url, timeout=45, **kwargs)
    r.raise_for_status()
    return r.json()

def children(session, parent):
    parent = parent.replace("\\", "\\\\").replace("'", "\\'")
    token = None
    while True:
        params = {"q": f"'{parent}' in parents and trashed = false", "fields": FIELDS,
                  "pageSize": 1000, "supportsAllDrives": "true", "includeItemsFromAllDrives": "true"}
        if token:
            params["pageToken"] = token
        data = request(session, API, params=params)
        yield from data.get("files", [])
        token = data.get("nextPageToken")
        if not token:
            break

def scan(folder_id, key_file):
    credentials = service_account.Credentials.from_service_account_file(
        key_file, scopes=["https://www.googleapis.com/auth/drive.readonly"])
    session = AuthorizedSession(credentials)
    try:
        root = request(session, f"{API}/{quote(folder_id, safe='')}",
                       params={"fields": "id,name,mimeType", "supportsAllDrives": "true"})
        if root.get("mimeType") != FOLDER:
            raise ValueError("指定 ID 不是文件夹")
        queue = deque([(folder_id, "")])
        seen = set()
        files = {}
        while queue:
            parent, prefix = queue.popleft()
            if parent in seen:
                continue
            seen.add(parent)
            for item in children(session, parent):
                mime = item.get("mimeType", "")
                name = item["name"]
                path = f"{prefix}/{name}" if prefix else name
                if mime == FOLDER:
                    queue.append((item["id"], path))
                elif mime != SHORTCUT and (mime.startswith("video/") or Path(name.lower()).suffix in EXTS):
                    fid = item["id"]
                    can = item.get("capabilities", {}).get("canDownload")
                    files[fid] = {
                        "id": fid, "name": name, "path": path, "size_bytes": int(item.get("size") or 0),
                        "mime_type": mime, "can_download": can,
                        "browser_view_url": item.get("webViewLink"),
                        "browser_download_url": item.get("webContentLink") if can is not False else None,
                        "api_download_url": f"{API}/{quote(fid, safe='')}?alt=media" if can is not False else None,
                        "api_auth_required": True
                    }
        return {"root_folder_id": folder_id, "root_folder_name": root.get("name"),
                "folders_scanned": len(seen),
                "files": sorted(files.values(), key=lambda x: x["path"].casefold())}
    finally:
        session.close()

def main():
    parser = argparse.ArgumentParser(description="Search Google Drive video metadata and URLs")
    parser.add_argument("--db", default=str(DB))
    commands = parser.add_subparsers(dest="command", required=True)
    s = commands.add_parser("scan")
    s.add_argument("--folder-id", default=os.getenv("GDRIVE_FOLDER_ID"))
    s.add_argument("--credentials", default=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
    q = commands.add_parser("search")
    q.add_argument("query")
    q.add_argument("--limit", type=int, default=30)
    l = commands.add_parser("link")
    l.add_argument("identifier")
    l.add_argument("--json", action="store_true")
    args = parser.parse_args()
    db = Path(args.db).expanduser()
    if args.command == "scan":
        if not args.folder_id or not args.credentials:
            parser.error("需要 --folder-id 和 --credentials 或对应的环境变量")
        result = scan(args.folder_id, args.credentials)
        db.parent.mkdir(parents=True, exist_ok=True)
        temp = db.with_suffix(".tmp")
        temp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(temp, 0o600)
        temp.replace(db)
        print(f"已索引 {len(result['files'])} 个视频，{result['folders_scanned']} 个文件夹")
        return
    data = json.loads(db.read_text(encoding="utf-8"))
    if args.command == "search":
        found = [x for x in data["files"] if args.query.casefold() in x["path"].casefold()]
        print(f"找到 {len(found)} 个结果")
        for x in found[:max(0, args.limit)]:
            print(f"{x['path']} | {x['size_bytes']} bytes | ID: {x['id']}")
    else:
        found = [x for x in data["files"] if x["id"] == args.identifier]
        if not found:
            found = [x for x in data["files"] if x["name"].casefold() == args.identifier.casefold()]
        if len(found) != 1:
            parser.error("未找到或名称不唯一；请先 search 并使用文件 ID")
        x = found[0]
        if args.json:
            print(json.dumps(x, ensure_ascii=False, indent=2))
        else:
            for k, v in x.items():
                print(f"{k}: {v}")
            print("API 地址需要 OAuth Bearer Token，非匿名直链。")

if __name__ == "__main__":
    main()
