import os
import sys
import optparse
import socket
import json

STATUS_CODE  = {
    250 : "Invalid cmd ",
    251 : "Invalid auth data",
    252 : "Wrong username or password",
    253 : "Passed authentication",
    254 : "File doesn't exist ",
    255 : "ready to send file",
    256 : "no access",

    800 : "the file exist,but not enough ,is continue? ",
    801 : "the file exist !",
    802 : " ready to receive datas",

    900 : "md5 valdate success"
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class ClinetHandle():
    def __init__(self):

        self.login_time = 1
        self.mainPath = BASE_DIR #设定主路径

        self.op = optparse.OptionParser() #读取参数

        #设定参数
        self.op.add_option("-s", "--server", dest="server")
        self.op.add_option("-P", "--port", dest="port")
        self.op.add_option("-u", "--username", dest="username")
        self.op.add_option("-p", "--password", dest="password")

        self.options, self.args = self.op.parse_args() #获得输入参数
        self.checkPort()
        self.makeConn()
        self.checkUser()

    # 检测端口号是否合法；
    def checkPort(self):
        if self.options.port is None :
            self.options.port = 8080  # 默认端口为8080
        elif int( self.options.port) > 0 and int(self.options.port) < 65535:
            return True
        else:
            exit("the port is in 0-65535")

     #建立socket链接
    def makeConn(self):
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.sock.connect((self.options.server,int(self.options.port)))
        print("FTP Server is runing")
        self.logIn()

    def logIn(self):
        if self.checkUser() :

            while True:
                self.cmdInfo()

        else:
            exit("try again")

    def cmdInfo(self):

        cmd_info = input("[%s]" % self.current_dir).strip()  # put 12.png images

        #不为空
        if cmd_info :
            cmd_list = cmd_info.split()
            getattr(self, cmd_list[0], self.cmdError)(*cmd_list)  #反射

    #检测是否输入用户名
    def checkUser(self):

        if self.options.username is None or self.options.password is None:
            self.options.username = input("username: ")
            self.options.password = input("password: ")
            return self.authResult(self.options.username, self.options.password)

        return self.authResult(self.options.username, self.options.password)

    #用户名检测
    def authResult(self ,username, password):
        self.sentData("auth", username = username, password = password)
        response = self.response()
        if response == "250":
            self.cmdError()
            return

        #判断是否登陆成功
        if response == "253":
            self.user = username
            self.current_dir = username
            print(STATUS_CODE[253])
            return True

        else:
            print(STATUS_CODE[252])
            if self.login_time == 3 :
                return False
            print("input again")
            self.options.username = input("username: ")
            self.options.password = input("password: ")
            self.login_time = self.login_time + 1
            return self.authResult(self.options.username, self.options.password)

    #上传
    def put(self, *cmd_list):
        if len(cmd_list) == 3:
            # put 12.png images
            action, local_path, target_path = cmd_list
            local_path = os.path.join(self.mainPath, local_path)
            file_name = os.path.basename(local_path)
            file_size = os.stat(local_path).st_size

            self.sentData("put", file_name = file_name, file_size = file_size, target_path = target_path)
            response = self.response()

            if response == "250":
                self.cmdError()
                return

            has_sent=0 #设置上传起始位置

            if response == "802":
                print(STATUS_CODE[802])


            if response == "800":
                #文件不完整
                choice = input("the file exist,but not enough,is continue?[Y/N]").strip()

                if choice.upper()=="Y":
                    self.sock.sendall("Y".encode("utf8"))
                    continue_position = self.sock.recv(1024).decode("utf8")
                    has_sent += int(continue_position) #更改上传起始位置

                else:
                    self.sock.sendall("N".encode("utf8"))

            elif response == "801":
                #文件完全存在
               print("the file exist")
               return

            f = open(local_path,"rb")
            f.seek(has_sent) #断点传送

            while has_sent < file_size:
                data = f.read(1024)
                self.sock.sendall(data)
                has_sent+= len(data)
                self.show_progress(has_sent, file_size)

            print("put success")
            f.close()
        else:
            self.cmdError()

    #下载
    def pull(self, *cmd_list):
        if len(cmd_list) == 3:
            action , file_path, dst_dir = cmd_list
            dst_path = os.path.join(self.mainPath, dst_dir, os.path.basename(file_path))

            if not os.path.isdir(os.path.join(self.mainPath, dst_dir)) :
                print("dir is not exist")
                return

            has_received = 0  #定义初始位置

            if os.path.exists(dst_path) :
                file_size = os.stat(dst_path).st_size
            else:
                file_size = 0

            self.sentData("pull", file_path = file_path, file_size = file_size)

            complete_size = int(self.sock.recv(1024).decode("utf8"))
            response = self.response()

            if response == "250":
                self.cmdError()
                return

            elif response == "800":
                # 文件不完整
                choice = input("the file exist,but not enough,is continue?[Y/N]").strip()

                if choice.upper() == "Y":
                    self.sock.sendall("Y".encode("utf8"))
                    has_received += int(file_size)  # 更改上传起始位置
                    f = open(dst_path, "ab")

                elif choice.upper() == "N":
                    self.sock.sendall("N".encode("utf8"))
                    f = open(dst_path, "wb")

                else:
                    print(STATUS_CODE[250])

            elif response == "801":
                # 文件完全存在
                print("the file exist")
                return

            elif response == "802":
                print(STATUS_CODE[802])
                f = open(dst_path, "wb")

            else:
                print(STATUS_CODE[254])
                return


            while has_received < complete_size:
                try:
                    data = self.sock.recv(1024)
                except Exception as e:
                    break
                f.write(data)
                has_received += len(data)
                self.show_progress(has_received, complete_size)

            print("pull success")
            f.close()

        else:
            self.cmdError()

    def ls(self, *cmd_list):
        if cmd_list[0] == "ls":
            self.sentData("ls")

            data = self.sock.recv(1024).decode("utf8") #可能会粘包？？看命吧....
            print(data)

        else:
            self.cmdError()

    def cd(self, *cmd_list):
        if cmd_list[0] == "cd" and len(cmd_list) == 2 :
            self.sentData("cd", dirname = cmd_list[1])

            data = self.sock.recv(1024).decode("utf8")
            if data == "256" :
                print(STATUS_CODE[256])
            else:
                self.current_dir = data

        else:
            self.cmdError()

    def mkdir(self, *cmd_list):
        if cmd_list[0] == "mkdir" and len(cmd_list) == 2:
            self.sentData("mkdir", dirname = cmd_list[1])

            print(self.sock.recv(1024).decode("utf8"))
        else:
            self.cmdError()

    #打印进度条
    def show_progress(self, has, total):
        rate = float(has) / float(total)
        rate = int(rate * 100)
        sys.stdout.write("%s%% %s\r"%(rate,"#"*int(rate/4)))

    def sentData(self,action,**kwargs):
        data = {
             "action": action,
              }

        for key, value in kwargs.items(): #遍历字典
            data[key] = value

        self.sock.send(json.dumps(data).encode("utf8"))

    def response(self):
        return self.sock.recv(1024).decode("utf8")


    def cmdError(self,*cmd_list):
        print("Error cmd")
        print("Try [ help]")

    def help(self,*cmd_list):
        print('''
        HELP:
        start : python FTP -[cmd]
        cmd:
        -s --server   Server_IP
        -P --port     Server_Port
        -u --username username
        -p --password password
        
        run ：[cmd] 
        cmd:
        pull:  pull [sourcedir+filename] [targetdir]
        cd:    cd [dir]
        ls:    ls
        mkdir: mkdir [dir]
        pull:  pull [src] [det]
        
        STATUS_CODE：
            250 : "Invalid cmd ",
            251 : "Invalid auth data",
            252 : "Wrong username or password",
            253 : "Passed authentication",
            254 : "File doesn't exist ",
            255 : "ready to send file",
            256 : "no access",
            800 : "the file exist,but not enough ,is continue? ",
            801 : "the file exist !",
            802 : " ready to receive datas",
            900 : "md5 valdate success"
        ''')

ch = ClinetHandle()


