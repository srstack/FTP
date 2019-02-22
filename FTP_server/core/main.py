import optparse
import socketserver
import configparser
import os
from conf import setting
from core import server

class SeverStart():
    def __init__(self):
        self.op = optparse.OptionParser()
        self.options, self.args = self.op.parse_args() #接收参数
        self.homePath = os.path.join(setting.BASE_DIR, "home")
        self.cmdInfo()

    def cmdInfo(self):
        cmd = self.args[0]
        getattr(self, cmd, self.help)()

    #建立链接，运行socketserver
    def start(self):
        print(" the server is working...")
        s = socketserver.ThreadingTCPServer((setting.IP,setting.PORT), server.ServerHandler)
        s.serve_forever()

    def createuser(self):
        username = input("input username: ")
        password = input("input password: ")
        auth_password = input("input password again: ")
        if password == auth_password :
            user = configparser.ConfigParser()
            user[username] = {
                "Password" : password ,
                "Quotation" : username,
            }
            with open(setting.ACCOUNT_PATH, 'a', encoding='utf8') as f : #新用户写入配置文件
                user.write(f)

            self.makeHomeDir(username)

        else:
            exit("create fail")

    def makeHomeDir(self,username):
        os.mkdir(os.path.join(self.homePath, username))  #创建用户文件夹




    def help(self):
        print(
        '''
         HELP:
         run       :  python FTP_server start
         help      :  python FTP_server help
         creareuer :  python FTP_server.py createuser
         
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
         '''
              )