# encoding:utf-8

import socket as sc
import os
import threading

HOST = '127.0.0.1'
PORT = 10010

PEERADDRPORT = ('127.0.0.1', 10086)

class P2Pclient():
    def __init__(self, desAddrPort):
        self.desAddrPort = desAddrPort
        self.client_socket = sc.socket(sc.AF_INET, sc.SOCK_STREAM)
        self.client_socket.connect(self.desAddrPort)

    def register(self):
        print("register to server, please wait...")
        self.client_socket.send('register'.encode())
        dataObj = self.client_socket.recv(1024)
        if not dataObj:
            return False
        elif dataObj.decode() == 'give files you have':
            peerShareList = os.listdir(os.path.join(os.path.abspath('.'), 'share'))
            self.client_socket.send(repr(peerShareList).encode())
            print("registration success")
            
            #给服务器我的被download地址端口
            dataObj1 = self.client_socket.recv(1024)
            if not dataObj:
                return False
            elif dataObj1.decode() == 'give your dowAddrPort':
                self.client_socket.send(repr(PEERADDRPORT).encode())
                print("give my address and port", PEERADDRPORT, "to server for other peers to download")

            #亟待建立一个非阻塞服务器用于下载?

            return True
        else:
            return False

    def getl(self):
        self.client_socket.send('get file list'.encode())
        listObj = self.client_socket.recv(1024)
        if not listObj:
            return False
        else:
            fileList = eval(listObj.decode())   #空列表？
            print(fileList)
            return True

    def dowf(self):
        self.client_socket.send('download file'.encode())
        dataObj = self.client_socket.recv(1024)
        if not dataObj:
            print('1 ', end = '')
            return False
        elif dataObj.decode() == 'filename':
            filename = input("input filename:")
            self.client_socket.send(filename.encode())
            ifExistObj = self.client_socket.recv(1024)   #4.18 18:22
            if not ifExistObj:
                print('2 ', end = '')
                return False
            elif ifExistObj.decode() == 'exist and ready':
                peerAddrPortListObj = self.client_socket.recv(1024) #接受含文件的peer list
                if not peerAddrPortListObj:
                    print('3 ', end = '')
                    return False
                else:
                    peerAddrPortList = eval(peerAddrPortListObj.decode())    #空列表...怎么办,不会是空列表的，否则就是不存在
                    
                    #重点，分片从peer下载，最好实现多线程下载

                    self.dowFromPeers(filename, peerAddrPortList)   #从peers下载文件的具体动作，是顺序下载
                    return True
                    
            elif ifExistObj.decode() == 'not exist':
                print("Sorry, we don't have " + filename + ' to download...')
                return True
            else:
                print('4 ', end ='')
                return False
        else:
            return False

    def logOut(self):
        self.client_socket.send('quit'.encode())
        dataObj = self.client_socket.recv(1024)
        if not dataObj:
            return False
        elif dataObj.decode() == 'log out success':
            print("log out success")
            return True
        else:
            return False

    def dowFromPeers(self, filename, peersList):
        #连接有文件peer的下载socket，而不是和服务器连接的socket呵呵
        #拓展：实现多线程下载
        print("downloading", filename, "from", peersList)
        #先顺序
        for i in range(len(peersList)):
            print("downloading", filename, i, '|', len(peersList), 'please wait...')
            s = sc.socket(sc.AF_INET, sc.SOCK_STREAM)
            s.connect(peersList[i])
            s.send(repr([filename, i, len(peersList)]).encode())
            dataObj = s.recv(1024)
            partFileSize = int(dataObj.decode())
            recievedSize = 0

            with open(filename + str(i), 'wb') as f:    #适应缓冲区下载过程
                while recievedSize < partFileSize:
                    remainSize = partFileSize - recievedSize
                    rs = 1024 if remainSize > 1024 else remainSize
                    recFile = s.recv(rs)
                    f.write(recFile)
                    recievedSize += rs
            print("completely download", filename, i, '|', len(peersList))

        print("completely downloaded all", filename)
        
        self.merf(filename, len(peersList)) #合并分片下载的文件

        self.delChunk(filename, len(peersList)) #删除分片
        
    def merf(self, filename, fileNumber):
        print("Merging files...")
        with open(filename, 'wb') as wf:
            for i in range(fileNumber):
                with open(filename + str(i), 'rb') as rf:
                    data = rf.read()
                    wf.write(data)
        print("completely merge files")
    #思考一个将下载完成的文件移到share文件夹供其他peer继续下载，注意，需要同时更新服务器上的fileList
    def delChunk(self, filename, fileNumber):
        for i in range(fileNumber):
            os.remove(filename + str(i))

class SendFileThread(threading.Thread):
    def run(self):
        sendFileSc = sc.socket(sc.AF_INET, sc.SOCK_STREAM)    #可用TCPserver，但先不用
        sendFileSc.bind(PEERADDRPORT)
        sendFileSc.listen(1)
        while True:  #待完成，希望是服务器？
            wantDowSc, wantDowAddrPort = sendFileSc.accept()    #完成一个peer的传输任务0以后accept是否可以继续接受其它peer
            print("\n* Peer", wantDowAddrPort, "is connecting...")
            dataObj = wantDowSc.recv(1024)  #[filename, number, segments]
            #远程主机强迫关闭了一个现有的连接
            if not dataObj:
                continue
            dataList = eval(dataObj.decode())
            filename = dataList[0]
            number = dataList[1]
            segments = dataList[2]
            print("* Peer", wantDowAddrPort, "want", filename, number, '|', segments)
            filePath = os.path.join(os.path.abspath('.'), 'share', filename)
            fileSize = os.path.getsize(filePath)
            stChunk = fileSize/segments
            start = int(stChunk*number)
            readSize = int(stChunk+fileSize%stChunk if number==segments-1 else stChunk)

            preSend = str(readSize)
            wantDowSc.send(preSend.encode()) #先送要传输的文件大小

            sentSize = 0
            with open(filePath, 'rb') as f:
                f.seek(start, 0)
                while sentSize < readSize:
                    remainSize = readSize - sentSize
                    sendSize = 1024 if remainSize > 1024 else remainSize
                    sendFile = f.read(sendSize)
                    sentSize += sendSize
                    wantDowSc.send(sendFile)
            wantDowSc.close()
            print("* completely send", filename, number, '|', segments)
            print(">>>", end = '')

def main():
    peer = P2Pclient((HOST, PORT))
    while peer.register() == False:
        print("Regiser fell, trying again now...")

    a_thread = SendFileThread() #创建供其他peer下载的地址接口，并传输文件
    a_thread.setDaemon(True)
    print("\n" + str(PEERADDRPORT) + "is open for other peers to download")
    a_thread.start()
    print("getl: get file list\ndowf: download file\nquit: quit and log out")
    while True:
        command = input(">>>")
        if command.lower() == 'getl':
            while peer.getl() == False:
                print("get file list fell, trying again now...")
        elif command.lower() == 'dowf':
            while peer.dowf() == False:
                print("down file fell, trying again now...")
        elif command.lower() == 'quit': #最好正常退出
            while peer.logOut() == False:
                print("log out fell, trying again now...")
            break


if __name__ == '__main__':
    main()