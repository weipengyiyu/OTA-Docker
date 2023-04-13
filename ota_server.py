#!/usr/bin/python
# -*- coding: UTF-8 -*-
# 本地测试启动 python http_server.py 8000
# linux服务器启动时，注意选择python3环境

# 忽略挂断信号 , 默认端口1234
# nohup python3 http_SERVER.py >> ../http_SERVER.log 2>&1 &

__version__ = "0.6.0"
__all__ = ["MyHTTPRequestHandler"]

import os
import time
import sys
import socket
import posixpath
import platform
import threading
try:
    from html import escape
except ImportError:
    from cgi import escape
import shutil
import mimetypes
import re
import signal
from io import BytesIO
import codecs
if sys.version_info.major == 3:
    # Python3
    from urllib.parse import quote
    from urllib.parse import unquote
    from http.server import HTTPServer
    from http.server import BaseHTTPRequestHandler
else:
    # Python2
    from urllib import quote
    from urllib import unquote
    from BaseHTTPServer import HTTPServer
    from BaseHTTPServer import BaseHTTPRequestHandler

"""
带有GET/HEAD/POST命令的简单HTTP请求处理程序。
提供来自当前目录及其任何子目录的文件,可以接收客户端上传的文件和文件夹。
GET/HEAD/POST请求完全相同，只是HEAD请求忽略了文件的实际内容。
"""


class MyHTTPRequestHandler(BaseHTTPRequestHandler):

    server_version = "simple_http_server/" + __version__

    mylist = []
    myspace = ""
    treefile = "dirtree.txt"
    IPAddress = socket.gethostbyname(socket.gethostname())

    def buildTree(self, url):
        print("directories url:", url)
        files = os.listdir(r''+url)
        # not show parent directory
        # self.mylist = []
        for file in files:
            if not file.startswith('.'):
                myfile = url + "/"+file
                size_str = bytes_conversion(myfile)
                if os.path.isfile(myfile):
                    self.mylist.append(
                        str(self.myspace)+"|____"+file + " " + size_str+"\n")
                elif os.path.isdir(myfile):
                    self.mylist.append(
                        str(self.myspace)+"|____"+file + "\n")
                    # get into the sub-directory, add "|    "
                    self.myspace = self.myspace+"|    "
                    self.buildTree(myfile)
                    # when sub-directory of iteration is finished, reduce "|    "
                    self.myspace = self.myspace[:-5]

    def getAllFilesList(self):
        listofme = []
        for root, dirs, files in os.walk(translate_path(self.path)):
            files.sort()
            for fi in files:
                display_name = os.path.join(root, fi)
                # 删除前面的n个字符，取出相对当前目录的路径
                relative_path = display_name[len(
                    os.getcwd()):].replace('\\', '/')[1:]
                if not relative_path.startswith('.'):
                    # print("display", display_name)
                    st = os.stat(display_name)
                    # fsize = st.st_size
                    fsize = bytes_conversion(display_name)
                    print("Size", str(os.path.getsize(display_name)))
                    fmtime = time.strftime(
                        '%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime))
                    listofme.append(relative_path+"\t")
                    listofme.append(fsize+"\t")
                    listofme.append(str(fmtime)+"\t\n")
        return listofme

    def calculate_dir_size(self, pathvar):
        '''
        calculate dir size(bytes)
        '''
        size = 0
        lst = os.listdir(pathvar)
        for i in lst:
            pathnew = os.path.join(pathvar, i)
            if os.path.isfile(pathnew):
                size += os.path.getsize(pathnew)
            elif os.path.isdir(pathnew):
                size += self.calculate_dir_size(pathnew)
        return size

    def writeList(self, url):
        tree_ = self.getAllFilesList()
        f = open(url, 'w', encoding="utf-8")
        f.write("http://"+str(self.IPAddress) +
                ":8000/ \ndirectory tree\n")
        # self.mylist.sort()
        f.writelines(self.mylist)
        f.write("\nFile Path\tFile Size\tFile Modify Time\n")
        f.writelines(tree_)
        self.mylist = []
        self.myspace = ""
        print("writing completed.")
        f.close()

    def do_GET(self):
        """Serve a GET request."""
        paths = unquote(self.path)
        path = str(paths)

        plist = path.split("/", 2)

        if len(plist) > 2 and plist[1] == "delete":
            result = plist[2]
            print("ready delete file/dir===>", result)
            if isWondows() and result.startswith("/"):
                result = result[1:]
            if os.path.exists(result):
                print("deleting file/dir===>", result)
                # dirn = os.path.dirname(result)
                if os.path.isdir(result):
                    shutil.rmtree(result)
                else:
                    os.remove(result)

                time.sleep(0.5)
                # 0.5s后重定向
                self.send_response(302)
                self.send_header('Location', "/")
                self.end_headers()
                return

        # 这个一定要放在后面，否则，怎么都不会重定向，一直卡在默认的404页面
        fd = self.send_head()
        # 查看当前的请求路径
        # 参考https://blog.csdn.net/qq_35038500/article/details/87943004
        if fd:
            # print("path===", path)
            shutil.copyfileobj(fd, self.wfile)
            # 只有回到根目录下才更新写入目录文件，保持最新
            if path == "/":
                self.mylist = []
                self.buildTree(translate_path(self.path))
                self.writeList(self.treefile)
            fd.close()

    def do_HEAD(self):
        """Serve a HEAD request."""
        fd = self.send_head()
        if fd:
            fd.close()

    def do_POST(self):
        """Serve a POST request."""
        r, info = self.deal_post_data()

        f = BytesIO()
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(b"<html>\n<title>Upload Result Page</title>\n")
        f.write(b"<body>\n<h2>Upload Result Page</h2>\n")
        f.write(b"<hr>\n")
        if r:
            f.write(b"<strong>Success:</strong><br>")
        else:
            f.write(b"<strong>Failed:</strong><br>")

        for i in info:
            f.write(i.encode('utf-8')+b"<br>")
        f.write(b"<br><a href=\"%s\">back</a>" %
                self.headers['referer'].encode('ascii'))
        f.write(b"</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html;charset=utf-8")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if f:
            shutil.copyfileobj(f, self.wfile)
            f.close()
        self.mylist = []
        # 每次提交post请求之后更新目录树文件
        self.buildTree(translate_path(self.path))
        self.writeList(MyHTTPRequestHandler.treefile)

        strcmd = "mosquitto_pub -h 30.178.38.62 -t 'wp/test' -m 'update file' -u ellison -P 1"
        os.system(strcmd)
        print(strcmd)

    def str_to_chinese(self, var):
        not_end = True
        while not_end:
            start1 = var.find("\\x")
            if start1 > -1:
                str1 = var[start1 + 2:start1 + 4]
                start2 = var[start1 + 4:].find("\\x") + start1 + 4
                if start2 > -1:
                    str2 = var[start2 + 2:start2 + 4]

                    start3 = var[start2 + 4:].find("\\x") + start2 + 4
                    if start3 > -1:
                        str3 = var[start3 + 2:start3 + 4]
            else:
                not_end = False
            if start1 > -1 and start2 > -1 and start3 > -1:
                str_all = str1 + str2 + str3
                str_all = codecs.decode(str_all, "hex").decode('utf-8')

                str_re = var[start1:start3 + 4]
                var = var.replace(str_re, str_all)
        return var

    def deal_post_data(self):
        boundary = self.headers["Content-Type"].split("=")[1].encode('ascii')
        print("boundary===", boundary)
        remain_bytes = int(self.headers['content-length'])
        print("remain_bytes===", remain_bytes)

        res = []
        line = self.rfile.readline()
        while boundary in line and str(line, encoding="utf-8")[-4:] != "--\r\n":

            remain_bytes -= len(line)
            if boundary not in line:
                return False, "Content NOT begin with boundary"
            line = self.rfile.readline()
            remain_bytes -= len(line)
            fn = re.findall(
                r'Content-Disposition.*name="file"; filename="(.*)"', str(line))
            if not fn:
                return False, "Can't find out file name..."
            path = translate_path(self.path)

            fname = fn[0]
            fname = self.str_to_chinese(fname)

            fn = os.path.join(path, fname)
            while os.path.exists(fn):
                fn += "_"

            dirname = os.path.dirname(fn)
            if not os.path.exists(dirname):
                os.makedirs(dirname)
            line = self.rfile.readline()
            remain_bytes -= len(line)
            line = self.rfile.readline()

            remain_bytes -= len(line)
            try:
                out = open(fn, 'wb')
            except IOError:
                return False, "Can't create file to write, do you have permission to write?"

            pre_line = self.rfile.readline()
            remain_bytes -= len(pre_line)
            Flag = True
            while remain_bytes > 0:
                line = self.rfile.readline()
                if boundary in line:
                    remain_bytes -= len(line)
                    pre_line = pre_line[0:-1]
                    if pre_line.endswith(b'\r'):
                        pre_line = pre_line[0:-1]
                    out.write(pre_line)
                    out.close()
                    res.append("File '%s' upload success!" % fn)
                    Flag = False
                    break
                else:
                    out.write(pre_line)
                    pre_line = line
            if pre_line is not None and Flag == True:
                out.write(pre_line)
                out.close()
                res.append("File '%s' upload success!" % fn)

        return True, res

    def send_head(self):
        """Common code for GET and HEAD commands.
        This sends the response code and MIME headers.
        Return value is either a file object (which has to be copied
        to the output file by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.
        """
        path = translate_path(self.path)
        if os.path.isdir(path):
            if not self.path.endswith('/'):
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        content_type = self.guess_type(path)
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)
        # self.send_header("Content-type", content_type)
        # Fix Messy Display
        self.send_header("Content-type", content_type+";charset=utf-8")
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f

    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).
        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().
        """
        try:
            list_dir = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list_dir.sort(key=lambda a: a.lower())
        f = BytesIO()
        display_path = escape(unquote(self.path))
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(b"<html>\n<title>OTA-SERVER %s</title>\n" %
                display_path.encode('utf-8'))
        f.write(b"<body>\n<h2>OTA-SERVER %s</h2>\n" %
                display_path.encode('utf-8'))
        f.write(b"<hr>\n")
        # 上传文件
        f.write(b"<h3>Files Updating</h3>\n")
        f.write(b"<form ENCTYPE=\"multipart/form-data\" method=\"post\">")
        f.write(b"<input ref=\"input\" multiple name=\"file\" type=\"file\"/>")
        f.write(b"<input type=\"submit\" value=\"uploadFiles\"/></form>\n")

        f.write(b"<hr>\n")
        # 表格
        f.write(b"<table with=\"100%\" style='text-align:center'>")
        f.write(b"<tr><th>path</th>")
        f.write(b"<th>type</th>")
        f.write(b"<th>size</th>")
        f.write(b"<th>modify time</th>")
        f.write(b"<th>operation</th>")
        f.write(b"</tr>")

        # 根目录下所有的内容
        for name in list_dir:
            # 根目录下的路径
            fullname = os.path.join(path, name)
            # 目录名/文件名
            display_name = linkname = name
            if not display_name.startswith('.'):
                if display_name == "ota_server.py" or display_name == "_config.yml":
                    continue

                # 如果是文件夹的话
                if os.path.isdir(fullname):
                    # 遍历文件夹
                    st = os.stat(fullname)

                    fsize = bytes_conversion(
                        "", self.calculate_dir_size(fullname))
                    fmtime = time.strftime(
                        '%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime))
                    relative_path = fullname[len(
                        os.getcwd()):].replace('\\', '/')
                    f.write(b"<tr>")
                    f.write(b'<td><a href="%s">%s</a></td>' % (
                        quote(relative_path).encode('utf-8'), escape("/"+display_name).encode('utf-8')))
                    ftype = "file"
                    if os.path.isdir(fullname):
                        ftype = "dir"
                    elif os.path.isfile(fullname):
                        ftype = "file"
                    f.write(b"<td>%s</td>" %
                            escape(ftype).encode('utf-8'))
                    f.write(b"<td>%s</td>" %
                            escape(fsize).encode('utf-8'))
                    f.write(b"<td>%s</td>" %
                            escape(fmtime).encode('ascii'))
                    f.write(b"<td><a style='border: solid 1px red; text-decoration: none; background: red; color: white;' href=\"/delete/%s\">delete</a>" %
                            escape(fullname).encode('utf-8'))
                    f.write(b"</tr>")

                # 如果是链接文件
                elif os.path.islink(fullname):
                    linkname = linkname + "/"
                    print("real link name ===", linkname)
                    display_name = name + "@"
                    # Note: a link to a directory displays with @ and links with /
                    f.write(b'<li><a href="%s">%s</a>\n' %
                            (quote(linkname).encode('ascii'), escape(display_name).encode('ascii')))

                else:
                    # 其他直接在根目录下的文件直接显示出来
                    st = os.stat(fullname)
                    fsize = bytes_conversion(fullname)
                    fmtime = time.strftime(
                        '%Y-%m-%d %H:%M:%S', time.localtime(st.st_mtime))
                    f.write(b"<tr>")
                    f.write(b'<td><a href="%s">%s</a></td>' %
                            (quote(linkname).encode('utf-8'), escape(display_name).encode('utf-8')))
                    ftype = "file"
                    if os.path.isdir(fullname):
                        ftype = "dir"
                    elif os.path.isfile(fullname):
                        ftype = "file"
                    f.write(b"<td>%s</td>" %
                            escape(ftype).encode('utf-8'))
                    f.write(b"<td>%s</td>" % escape(fsize).encode('utf-8'))
                    f.write(b"<td>%s</td>" % escape(fmtime).encode('ascii'))
                    f.write(b"<td><a href=\"/delete/%s\">delete</a>" %
                            escape(fullname).encode('utf-8'))
                    f.write(b"</tr>")

        f.write(b"</table>")
        f.write(b"\n<hr>\n</body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html;charset=utf-8")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f

    def guess_type(self, path):
        """Guess the type of a file.
        Argument is a PATH (a filename).
        Return value is a string of the form type/subtype,
        usable for a MIME Content-type header.
        The default implementation looks the file's extension
        up in the table self.extensions_map, using application/octet-stream
        as a default; however it would be permissible (if
        slow) to look inside the data to make a better guess.
        """

        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']

    if not mimetypes.inited:
        mimetypes.init()  # try to read system mime.types
    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream',  # Default
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
        '.txt': 'text/plain',
    })


def isWondows():
    '''
    判断当前运行平台
    :return:
    '''
    sysstr = platform.system()
    if (sysstr == "Windows"):
        return True
    elif (sysstr == "Linux"):
        return False
    else:
        print ("Other System ")
    return False


def translate_path(path):
    """Translate a /-separated PATH to the local filename syntax.
    Components that mean special things to the local file system
    (e.g. drive or directory names) are ignored.  (XXX They should
    probably be diagnosed.)
    """
    # abandon query parameters
    path = path.split('?', 1)[0]
    path = path.split('#', 1)[0]
    path = posixpath.normpath(unquote(path))
    words = path.split('/')
    words = filter(None, words)
    path = os.getcwd()
    for word in words:
        drive, word = os.path.splitdrive(word)
        head, word = os.path.split(word)
        if word in (os.curdir, os.pardir):
            continue
        path = os.path.join(path, word)
    return path


def bytes_conversion(file_path, total_size=-1):
    """
    calculate file size and dynamically convert it to K, M, GB, etc.
    :param file_path:
    :param total_size: the size of a dir
    :return: file size with format
    """
    number = 0
    if total_size == -1:
        number = os.path.getsize(file_path)
    else:
        number = total_size
    symbols = ('K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y')
    prefix = dict()
    for a, s in enumerate(symbols):
        prefix[s] = 1 << (a + 1) * 10
    for s in reversed(symbols):
        if int(number) >= prefix[s]:
            value = float(number) / prefix[s]
            return '%.2f%s' % (value, s)
    return "%sB" % number

# global t1, t2

def signal_handler(signal, frame):
    print("You choose to stop me.")
    
    # # 等待运行结束
    # t1.join()
    # t2.join()
    exit()


def http_mqtt_server(threadname):
    port = 8000
    server_address = ('', port)

    httpd = HTTPServer(server_address, MyHTTPRequestHandler)
    server = httpd.socket.getsockname()
    print("server_version: " + MyHTTPRequestHandler.server_version +
          ", python_version: " + MyHTTPRequestHandler.sys_version)
    print("Serving HTTP on: " +
          str(server[0]) + ", port: " + str(server[1]) + " ...")
    httpd.serve_forever()

def get_file_content(file_name):
    """获取文件的内容"""
    try:
        with open(file_name, "rb") as f:
            content = f.read()
        return content
    except:
        print("没有下载的文件:%s" % file_name)


def tcp_file_server(threadname):
    port = 7890
    # 创建socket
    tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 本地信息
    address = ('', port)
    # 绑定本地信息
    tcp_server_socket.bind(address)
    # 将主动套接字变为被动套接字
    tcp_server_socket.listen(128)

    while True:
        # 等待客户端的链接，即为这个客户端发送文件
        client_socket, clientAddr = tcp_server_socket.accept()
        # 接收对方发送过来的数据
        recv_data = client_socket.recv(1024)  # 接收1024个字节
        file_name = recv_data.decode("utf-8")
        print("对方请求下载的文件名为:%s" % file_name)
        file_content = get_file_content(file_name)
        # 发送文件的数据给客户端
        # 因为获取打开文件时是以rb方式打开，所以file_content中的数据已经是二进制的格式，因此不需要encode编码
        if file_content:
            client_socket.send(file_content)
        # 关闭这个套接字
        client_socket.close()

    # 关闭监听套接字
    tcp_server_socket.close()

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 创建两个线程
    try:
        # 初始化2个线程，传递不同的参数
        t1 = threading.Thread(target=http_mqtt_server, args=("http_mqtt_server",))
        t2 = threading.Thread(target=tcp_file_server, args=("tcp_file_server",))
        # 开启线程
        t1.start()
        t2.start()
    except:
        print ("Error: 无法启动线程")

if __name__ == '__main__':
    main()
