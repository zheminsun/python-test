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

app = Bottle()

@app.route('/')
def read_root():
    return {"message": "Hello, World!"}

def download_caddy():
    caddy_url = "https://github.com/caddyserver/caddy/releases/download/v2.4.6/caddy_2.4.6_linux_amd64.tar.gz"
    file_name = "caddy.tar.gz"
    urllib.request.urlretrieve(caddy_url, file_name)
    print("Caddy downloaded.")
    return file_name

def extract_caddy(file_name):
    if file_name.endswith("tar.gz"):
        tar = tarfile.open(file_name, "r:gz")
        tar.extractall()
        tar.close()
        print("Caddy extracted.")
    else:
        print("File format not recognized.")

def create_caddyfile():
    caddyfile_content = """
    :10001 {
        reverse_proxy /pythontest http://localhost:10086 {
            header_up Host {http.request.header.Host}
            header_up X-Real-IP {http.request.header.X-Real-IP}
            header_up X-Forwarded-For {http.request.header.X-Forwarded-For}
            header_up X-Forwarded-Proto {http.request.header.X-Forwarded-Proto}
            header_up Upgrade "websocket"
            header_up Connection "Upgrade"
        }
        reverse_proxy /ht http://localhost:10000 {
            header_up Host {http.request.header.Host}
            header_up X-Real-IP {http.request.header.X-Real-IP}
            header_up X-Forwarded-For {http.request.header.X-Forwarded-For}
            header_up X-Forwarded-Proto {http.request.header.X-Forwarded-Proto}
        }
    }

    """
    with open("Caddyfile", "w") as file:
        file.write(caddyfile_content)
    print("Caddyfile created.")

def start_caddy():
    # 确保Caddy文件具有执行权限
    subprocess.call(["chmod", "+x", "caddy"])
    # 使用subprocess启动Caddy
    subprocess.Popen(["./caddy", "run"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    print("Caddy started.")


def save_json_to_file(file_path):
    data = {
        "log": {"loglevel": "debug"},
        "inbounds": [
            {
                "port": 10001,
                "tag": "inbound-dokodemo",
                "protocol": "dokodemo-door",
                "settings": {
                    "network": "tcp",
                    "allowTransparent": True,
                    "followRedirect": True,
                },
                "sniffing": {"enabled": True, "destOverride": ["http", "tls"]},
                "streamSettings": {"sockopt": {"tproxy": "redirect"}},
            },
            {
                "port": 10086,
                "tag": "inbound-vless",
                "protocol": "vless",
                "settings": {
                    "clients": [
                        {
                            "id": "0e9fe21c-78b5-4ef8-87f7-40b7d2ffac75",
                            "level": 0,
                            "email": "email@example.com",
                        }
                    ],
                    "decryption": "none",
                },
                "streamSettings": {"network": "ws", "security": "none", "wsSettings": {
                    "path": "/vlws"
                }},
            },
        ],
        "outbounds": [
            {"protocol": "freedom", "settings": {}, "tag": "direct"},
            {
                "protocol": "freedom",
                "settings": {"redirect": "127.0.0.1:10086"},
                "tag": "to-vless",
            },
            {
                "protocol": "freedom",
                "settings": {"redirect": "127.0.0.1:10000"},
                "tag": "inner-http",
            },
        ],
        "dns": {"servers": ["1.1.1.1", "8.8.8.8"]},
        "routing": {
            "domainStrategy": "AsIs",
            "rules": [
                {
                    "type": "field",
                    "inboundTag": ["inbound-dokodemo"],
                    "outboundTag": "inner-http",
                },
                {
                    "type": "field",
                    "inboundTag": ["inbound-vless"],
                    "outboundTag": "direct",
                },
            ],
        },
    }

    with open(file_path+"/config.json", 'w') as file:
        json.dump(data, file, indent=4)

def download_files(file_path):
    file_urls = [
        "https://github.com/eooce/test/releases/download/123/web"
    ]

    for file_url in file_urls:
        file_name = file_url.split('/')[-1]
        file_path1 = os.path.join(file_path, file_name)

        if os.path.exists(file_path1):
            print(f"{file_path1} already exists, Skipping download")
        else:
            try:
                os.makedirs(file_path, exist_ok=True)
                with urllib.request.urlopen(file_url) as response, open(file_path1, 'wb') as out_file:
                    data = response.read()
                    out_file.write(data)
                print(f"Downloading {file_name}")
            except subprocess.CalledProcessError as e:
                print(f"Error starting Xray: {e}")
            except FileNotFoundError as e:
                print(f"Error: {e}. Please check if the Xray executable path is correct.")
            except Exception as e:
                print(f"An error occurred: {e}")
            os.chmod(file_path1, 0o755)

def download_and_unzip(url, extract_to='.'):
    """
    下载ZIP文件并解压到指定目录
    :param url: ZIP文件的URL
    :param extract_to: 解压目录
    """
    # 文件名从URL中提取
    file_name = url.split('/')[-1]
    
    if os.path.exists(extract_to):
        print(f"{extract_to} already exists, Skipping download")
    else:
        # 下载ZIP文件
        print(f"Downloading {file_name}...")
        with urllib.request.urlopen(url) as response:
            with open(file_name, 'wb') as out_file:
                out_file.write(response.read())
        print(f"Downloaded {file_name}.")

        # 解压ZIP文件
        print(f"Extracting {file_name}...")
        with zipfile.ZipFile(file_name, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        print(f"Extracted to {extract_to}.")

        # 清理，删除ZIP文件
        os.remove(file_name)
        print(f"Deleted {file_name}.")

def rename_and_set_permissions():
    old_path = './world/xray'
    new_path = './world/web'
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
        print(f"Error: Permission denied when renaming or setting permissions for {new_path}.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def find_and_kill_process(command):
    # 遍历当前活动的进程
    for proc in psutil.process_iter(['cmdline']):
        # 检查进程命令行是否匹配
        if command in ' '.join(proc.info['cmdline']):
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
        proc_ids = subprocess.check_output(['pgrep', '-f', process_name]).decode().strip().split('\n')
        
        for pid in proc_ids:
            if pid:  # 确保 pid 不为空
                print(f"Killing process ID {pid}...")
                # 使用 kill -9 强制终止进程
                subprocess.run(['kill', '-9', pid])
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
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        print("web server started successfully.")
    except Exception as e:
        print(f"Error starting Xray: {e}")


    

if __name__ == "__main__":
    #download_files("./world")
    download_url = 'https://github.com/XTLS/Xray-core/releases/download/v1.8.11/Xray-linux-64.zip'
    download_and_unzip(download_url, './world')
    rename_and_set_permissions()
    save_json_to_file("./world")
    kill_process_by_name("./world/web -c ./world/config.json")
    start_xray("./world")  
    
    if os.path.exists("caddy"):
        print(f"caddy已经存在")
    else:
        file_name = download_caddy()
        extract_caddy(file_name)
        create_caddyfile()
    kill_process_by_name("./caddy run")
    #start_caddy()  
    
    run(app, host='0.0.0.0', port=10000)
