import socketserver
import os
import json
import configparser
from conf import setting

STATUS_CODE  = {
    250 : "Invalid cmd ",
    251 : "Invalid auth data",
    252 : "Wrong username or password",
    253 : "Passed authentication",
    254 : "File doesn't exist ",
    255 : "ready to send file",
    256: "no access",

    800 : "the file exist,but not enough ,is continue? ",
    801 : "the file exist !",
    802 : " ready to receive datas",

    900 : "md5 valdate success"
}

class ServerHandler( socketserver.BaseRequestHandler ):

    def handle(self):
        while True:
            data = json.loads(self.request.recv(1024).strip().decode("utf8"))

            if data.get("action"):
                print(data)
                getattr(self, data.get("action"), self.cmdInvalid)(**data)  #反射
            else:
                self.cmdInvalid()

    def auth(self,**data):
        username = data["username"]
        password = data["password"]
        user = self.authEnticate(username, password)

        if user :
            self.responseSent(253)
        else:
            self.responseSent(252)

    def authEnticate(self, username, password):
        cfg = configparser.ConfigParser()
        cfg.read(setting.ACCOUNT_PATH)

        if username in cfg.sections():

            if cfg[username]["password"] == password:
                self.username = username
                print(self.username,"login success")
                if username == "root":
                    self.mainPath = os.path.join(setting.BASE_DIR, "root")
                else:
                    self.mainPath = os.path.join(setting.BASE_DIR, "home", self.username)
                self.current_dir = self.mainPath
                return username

    def put(self, **data):
        file_name = data.get("file_name")
        file_size = data.get("file_size")
        target_path = data.get("target_path")

        abs_path = os.path.join(self.current_dir, target_path, file_name)

        has_received = 0 #设置传送起始位置

        if os.path.exists( abs_path ):
            file_has_size = os.stat(abs_path).st_size # 赋值后避免多次计算文件大小

            if file_has_size < file_size:
                #断点续传
                self.responseSent(800)
                choice = self.request.recv(1024).decode("utf8")

                if choice == "Y":
                    self.request.sendall(str(file_has_size).encode("utf8"))
                    has_received+=file_has_size
                    f = open(abs_path, "ab")  #追加

                else :
                    f = open(abs_path, "wb")  #覆盖写

            else:
                self.responseSent(801)
                return

        else:
            self.responseSent(802)
            f = open(abs_path, "wb")


        while has_received < file_size :

            try:
                data=self.request.recv(1024)
            except Exception as e:
                break   #异常中断

            f.write(data)
            has_received+=len(data)

        print("put success")
        f.close()


    #下载
    def pull(self, **data):
        file_path = data.get("file_path")
        file_has_size = data.get("file_size")

        abs_path = os.path.join(self.current_dir, file_path)

        has_sent = 0  # 设置传送起始位置

        if os.path.exists(abs_path):
            file_size = os.stat(abs_path).st_size  # 赋值后避免多次计算文件大小

            self.request.sendall(str(file_size).encode("utf8"))

            if file_has_size == 0:
                self.responseSent(802)

            elif file_has_size < file_size:
                # 断点续传
                self.responseSent(800)
                choice = self.request.recv(1024).decode("utf8")

                if choice == "Y":
                    has_sent = file_has_size + has_sent

            else:
                self.responseSent(801)
                return

        else:
            self.request.sendall("0".encode("utf8"))
            self.responseSent(254)
            return

        f = open(abs_path, "rb")
        f.seek(has_sent)  # 断点传送

        while has_sent < file_size:

            data = f.read(1024)
            self.request.sendall(data)
            has_sent = has_sent + len(data)

        print("pull success")
        f.close()


    def ls(self, **data):
        file_list=os.listdir(self.current_dir)

        file_str="\n".join(file_list)  # 拼接
        if not len(file_list):
            file_str="<empty dir>"
        self.request.sendall(file_str.encode("utf8")) #可能会粘包....

    def cd(self, **data):
        dirname = data.get("dirname")

        if self.username == "root":
            if dirname == "..":
                self.current_dir = os.path.dirname(self.current_dir)
                self.request.sendall(os.path.basename(self.current_dir).encode("utf8"))
            else:
                self.current_dir = os.path.join(self.current_dir, dirname)
                self.request.sendall(os.path.basename(self.current_dir).encode("utf8"))
        else:
            if dirname == "..":
                self.current_dir = os.path.dirname(self.current_dir)

                if not os.path.basename(self.mainPath) in os.path.split(self.current_dir) :
                    self.responseSent(256)
                else:
                    self.request.sendall(os.path.basename(self.current_dir).encode("utf8"))
            else:
                self.current_dir = os.path.join(self.current_dir,dirname)

                if not os.path.basename(self.mainPath) in os.path.split(self.current_dir) :
                    self.responseSent(256)
                else:
                    self.request.sendall(os.path.basename(self.current_dir).encode("utf8"))

    def mkdir(self, **data):
        dirname = data.get("dirname")

        path = os.path.join(self.current_dir, dirname)

        if not os.path.exists(path):
            if "/" in dirname:
                os.makedirs(path)
            else:
                os.mkdir(path)
            self.request.sendall("create success".encode("utf8"))
        else:
            self.request.sendall("dirname exist".encode("utf8"))

    def cmdInvalid(self):   #返回错误码
        self.responseSent(250)

    def responseSent(self,state_code):
        response = str(state_code)
        self.request.sendall(response.encode("utf8"))

