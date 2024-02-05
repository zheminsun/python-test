import time
import datetime

# 以下是一个简单的Python程序，使用一个无限循环来保持程序一直运行，并且每隔10分钟打印当前时间

while True:
    # 在这里编写你的程序逻辑
    current_time = datetime.datetime.now()
    print("Current time:", current_time)

    # 暂停 10 分钟
    time.sleep(600)  # 10分钟 = 600秒
