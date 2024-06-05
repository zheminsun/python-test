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

@app.route('/ht')
def read_root():
    return {"message": "Hello, World!"}


    

if __name__ == "__main__":
    run(app, host='0.0.0.0', port=10001)
