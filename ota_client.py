#!/usr/bin/python3

import socket
import time
import paho.mqtt.client as mqtt
import os 
import docker
import sys
import threading
import signal

# 创建一个信号量，计数器初始值为0
semaphore = threading.Semaphore(0)

def tcp_update_file():
    # 创建socket
    tcp_client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 链接服务器
    tcp_client_socket.connect(("30.178.38.62", 7890))
    file_name = "docker_app.rar"
    # 发送文件下载请求
    tcp_client_socket.send(file_name.encode("utf-8"))
    # 把数据写入到文件里
    with open("./" + file_name, "wb") as file:
        while True:
            # 循环接收文件数据
            file_data = tcp_client_socket.recv(1024)
            # 接收到数据
            if file_data:
                # 写入数据
                file.write(file_data)
            # 接收完成
            else:
                print("下载结束！")
                break
    # 关闭套接字
    tcp_client_socket.close()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected with result code " + str(rc))

def on_message(client, userdata, msg):
    # 开始执行容器的复位或重置
    semaphore.release()


def reset_container():

    while True:
        #等待MQTT收到更新文件指令
        semaphore.acquire()
        # 查询所有存在的容器ID
        client = docker.from_env()
        # 获取所有容器ID
        container_ids = [container.id for container in client.containers.list()]
        # print(container_ids)

        #关闭所有容器
        for container_id in container_ids:
            strcmd = "docker kill -s KILL " + str(container_id)
            os.system(strcmd)        

        #删除当前目录所有文件
        strcmd = "rm -rf *"
        os.system(strcmd)
        
        # 下载更新文件
        tcp_update_file()
        #解压文件
        strcmd = "unrar e *.rar"
        os.system(strcmd)

        #重启容器
        strcmd = "docker run -it -v /home/wp/ota-client:/root -d weipengyiyu/ubuntu:18.04"
        os.system(strcmd)

        #执行应用程序启动命令
        strcmd = "python3 app_update.py"
        os.system(strcmd)

def sub_mqtt():
    # sub topic: wp/test
    client = mqtt.Client(client_id="", transport='tcp')
    client.username_pw_set("ellison", password="1")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(host="30.178.38.62", port = 1883, keepalive=60)  # 订阅频道
    time.sleep(1)
    client.subscribe([("public", 0), ("wp/test", 2)])
    client.loop_forever()


def signal_handler(signal, frame):
    print("You choose to stop me.")
    
    # # 等待运行结束
    # t1.join()
    # t2.join()
    exit()

def main():

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 创建两个线程
    try:
        # 初始化2个线程，传递不同的参数
        t1 = threading.Thread(target=sub_mqtt, args=())
        t2 = threading.Thread(target=reset_container, args=())
        # 开启线程
        t1.start()
        t2.start()
    except:
        print ("Error: 无法启动线程")
    # # 等待运行结束
    # t1.join()
    # t2.join()

if __name__ == "__main__":
    main()


