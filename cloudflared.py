import os
import time
import urllib.request
import subprocess
import json
import tarfile
import zipfile
import psutil
import signal
from bottle import Bottle, run
from datetime import datetime

app = Bottle()

@app.route("/ht")
def read_root():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {"message": "Hello, World!", "time": current_time}


def save_json_to_file(file_path):
    data = {
        "log": {"access": "/dev/null", "error": "/dev/null", "loglevel": "none"},
        "inbounds": [
            {
                "port": 4956,
                "protocol": "vless",
                "settings": {
                    "clients": [
                        {
                            "id": "986e0d08-b275-4dd3-9e75-f3094b36fa2a"
                        }
                    ],
                    "decryption": "none",
                    "fallbacks": [
                        {"dest": 55390},
                        {"path": "/vless", "dest": 48824},
                    ],
                },
                "streamSettings": {"network": "tcp"},
            },
            {
                "port": 48824,
                "listen": "127.0.0.1",
                "protocol": "vless",
                "settings": {
                    "clients": [
                        {"id": "986e0d08-b275-4dd3-9e75-f3094b36fa2a", "level": 0}
                    ],
                    "decryption": "none",
                },
                "streamSettings": {
                    "network": "ws",
                    "security": "none",
                    "wsSettings": {"path": "/vless"},
                },
                "sniffing": {
                    "enabled": True,
                    "destOverride": ["http", "tls", "quic"],
                    "metadataOnly": False,
                },
            }
        ],
        "dns": {"servers": ["https+local://8.8.8.8/dns-query"]},
        "outbounds": [
            {"protocol": "freedom"},
            {
                "tag": "WARP",
                "protocol": "wireguard",
                "settings": {
                    "secretKey": "YFYOAdbw1bKTHlNNi+aEjBM3BO7unuFC5rOkMRAz9XY=",
                    "address": [
                        "172.16.0.2/32",
                        "2606:4700:110:8a36:df92:102a:9602:fa18/128",
                    ],
                    "peers": [
                        {
                            "publicKey": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
                            "allowedIPs": ["0.0.0.0/0", "::/0"],
                            "endpoint": "162.159.193.10:2408",
                        }
                    ],
                    "reserved": [78, 135, 76],
                    "mtu": 1280,
                },
            },
        ],
        "routing": {
            "domainStrategy": "AsIs",
            "rules": [
                {
                    "type": "field",
                    "domain": ["domain:openai.com", "domain:ai.com"],
                    "outboundTag": "WARP",
                }
            ],
        },
    }

    with open(file_path + "/config.json", "w") as file:
        json.dump(data, file, indent=4)


def download_and_unzip(url, extract_to="."):
    """
    下载ZIP文件并解压到指定目录
    :param url: ZIP文件的URL
    :param extract_to: 解压目录
    """
    # 文件名从URL中提取
    file_name = url.split("/")[-1]

    if os.path.exists(extract_to):
        print(f"{extract_to} already exists, Skipping download")
    else:
        # 下载ZIP文件
        print(f"Downloading {file_name}...")
        with urllib.request.urlopen(url) as response:
            with open(file_name, "wb") as out_file:
                out_file.write(response.read())
        print(f"Downloaded {file_name}.")

        # 解压ZIP文件
        print(f"Extracting {file_name}...")
        with zipfile.ZipFile(file_name, "r") as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"Extracted to {extract_to}.")

        # 清理，删除ZIP文件
        os.remove(file_name)
        print(f"Deleted {file_name}.")


def rename_and_set_permissions():
    old_path = "./world/xray"
    new_path = "./world/web"
    if not os.path.exists(old_path):
        return
    try:
        # Rename the directory
        os.rename(old_path, new_path)
        print(f"Renamed {old_path} to {new_path}")

        # Set the permissions to 755
        os.chmod(new_path, 0o755)
        print(f"Set permissions of {new_path} to 755")

    except FileNotFoundError:
        print(f"Error: {old_path} does not exist.")
    except PermissionError:
        print(
            f"Error: Permission denied when renaming or setting permissions for {new_path}."
        )
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def find_and_kill_process(command):
    # 遍历当前活动的进程
    for proc in psutil.process_iter(["cmdline"]):
        # 检查进程命令行是否匹配
        if command in " ".join(proc.info["cmdline"]):
            print(f"找到进程: {proc.pid}, 正在杀死...")
            try:
                # 杀死进程
                os.kill(proc.pid, signal.SIGKILL)
                print(f"进程 {proc.pid} 已被杀死。")
            except Exception as e:
                print(f"杀死进程 {proc.pid} 时发生错误: {e}")


def kill_process_by_name(process_name):
    try:
        # 使用 pgrep 查找所有匹配的进程ID
        # 注意：-f 参数使 pgrep 在完整的命令行中查找模式
        proc_ids = (
            subprocess.check_output(["pgrep", "-f", process_name])
            .decode()
            .strip()
            .split("\n")
        )

        for pid in proc_ids:
            if pid:  # 确保 pid 不为空
                print(f"Killing process ID {pid}...")
                # 使用 kill -9 强制终止进程
                subprocess.run(["kill", "-9", pid])
                print(f"Process ID {pid} has been killed.")
    except subprocess.CalledProcessError as e:
        # 如果 pgrep 没有找到任何进程，会抛出异常
        print(f"No process found for {process_name}.")
    except Exception as e:
        print(f"Error: {e}")


def start_xray(xray_path):
    # 设置Xray配置文件的路径
    xray_config = xray_path + "/config.json"

    # 构造启动Xray的命令
    command = [xray_path + "/web", "-c", xray_config]

    # 使用subprocess模块执行命令
    try:
        # subprocess.DEVNULL用于忽略输出
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        print("web server started successfully.")
    except Exception as e:
        print(f"Error starting Xray: {e}")

def add_cloudflare_tunnel(package_name = "cloudflared"):
    if is_installed(package_name):
        print(f"{package_name} is installed. Uninstalling now...")
        uninstall_package(package_name)
    else:
        print(f"{package_name} is not installed. now installing...")
    # 定义要执行的命令
    commands = [
        "curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb",
        "sudo dpkg -i cloudflared.deb",
        "sudo cloudflared service install eyJhIjoiMWQzOGFjODVkM2NjNDY4ZGQ5YjQxM2VhZmNlZjQxOTIiLCJ0IjoiYjM5MzczMDEtZjM1NS00Y2Q2LTkwMmItYzMxMmExZjJiZmUyIiwicyI6Ik5tWXpPVEUyT0RVdE5Ua3haUzAwT0dNMExXRTFPREF0TkdOaVpXVXlNRFEwTmpZMSJ9"
    ]

    # 逐个执行命令
    for command in commands:
        process = subprocess.run(command, shell=True, check=True, text=True)
        if process.returncode != 0:
            print(f"Command failed: {command}")
            break

def is_installed(package_name):
    try:
        result = subprocess.run(['dpkg', '-l', package_name], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return package_name in result.stdout
    except subprocess.CalledProcessError:
        return False

def install_package(package_file):
    try:
        subprocess.run(['sudo', 'dpkg', '-i', package_file], check=True, text=True)
        print(f"{package_file} installed successfully.")
    except subprocess.CalledProcessError:
        print(f"Failed to install {package_file}.")
        subprocess.run(['sudo', 'apt-get', 'install', '-f'], check=True, text=True)

def uninstall_package(package_name):
    try:
        subprocess.run(['sudo', 'dpkg', '-r', package_name], check=True, text=True)
        print(f"{package_name} uninstalled successfully.")
    except subprocess.CalledProcessError:
        print(f"Failed to uninstall {package_name}.")
        subprocess.run(['sudo', 'apt-get', 'install', '-f'], check=True, text=True)

if __name__ == "__main__":
    # download_files("./world")
    download_url = (
        "https://github.com/XTLS/Xray-core/releases/download/v1.8.11/Xray-linux-64.zip"
    )
    download_and_unzip(download_url, "./world")
    rename_and_set_permissions()
    save_json_to_file("./world")
    kill_process_by_name("./world/web -c ./world/config.json")
    start_xray("./world")

    add_cloudflare_tunnel("cloudflared")

    run(app, host="0.0.0.0", port=55390)
