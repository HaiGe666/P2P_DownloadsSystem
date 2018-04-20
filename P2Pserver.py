#encoding:utf-8

import socketserver

fileDir = {}    #临界资源，是否要加锁？待升级强制关闭连接需要清理fileDir，强制退出待清空字典！！！

class PeerMsg():
    def __init__(self, addrPort, peerObj):
        self.addrPort = addrPort
        self.peerObj = peerObj

class P2Pserver(socketserver.BaseRequestHandler):
    def handle(self):
        """main while for server to handle each connection"""
        try:
            print("Get connection from", self.client_address)
            while(True):
                peerObj = self.request
                data = peerObj.recv(1024)
                if not data:
                    continue
                if data.decode() == 'register':
                    self.register(peerObj)
                    continue
                elif data.decode() == 'get file list':
                    print(self.client_address, "want to get file list")
                    fileList = list(fileDir.keys())
                    fileList.sort()
                    peerObj.send(repr(fileList).encode())
                    print("file list has sent to", self.client_address)
                    continue
                elif data.decode() == 'download file':
                    self.dowf(peerObj)
                    continue
                elif data.decode() == 'quit':
                    print(self.client_address, "want to quit")
                    self.delDirPeerMsg(peerObj)
                    peerObj.send('log out success'.encode())
                    print(self.client_address, "has logged out")
                    break
        except ConnectionResetError:
            print("!!! peer", self.client_address, "Remote host forcibly closes an existing connection and terminates with his connection")

    def delDirPeerMsg(self, peerObj):
        delKeys = []
        for key,value in fileDir.items():   #删除表中退出peer的信息
            for c in value:
                if c.peerObj == peerObj:
                    fileDir[key].remove(c)  #前提是列表中只有一个此peer信息
            if not value:   #删除文件名的peer列表为空状况
                delKeys.append(key)
        for delKey in delKeys:  #不能在遍历字典时删除键
            del fileDir[delKey]

    def register(self, peerObj):
        print(self.client_address, "want to register...")
        peerObj.send('give files you have'.encode())
        filenamesObj = peerObj.recv(1024)    #空列表也不是空
        if not filenamesObj:
            return
        filenames = eval(filenamesObj.decode())
        peerObj.send('give your dowAddrPort'.encode())
        dowAddrPortObj = peerObj.recv(1024)
        if not dowAddrPortObj:
            return    #是否应该continue?不管了
        dowAddrPort = eval(dowAddrPortObj.decode())
        print("get the register peer download address and port", dowAddrPort)
        for a_filename in filenames:
            a_PeerMsg = PeerMsg(dowAddrPort, peerObj)
            if a_filename not in fileDir:  #判断在fileList中是否存在这个文件名
                fileDir[a_filename] = [a_PeerMsg]
            else:
                fileDir[a_filename].append(a_PeerMsg)
        print(self.client_address, "register success...")
        return

    def dowf(self, peerObj):
        print(self.client_address, "want to download file")
        peerObj.send('filename'.encode())
        wantFilenameObj = peerObj.recv(1024)
        if not wantFilenameObj:
            return
        wantFilename = wantFilenameObj.decode()
        print(self.client_address,"want", wantFilename)
        if wantFilename in fileDir:
            peerObj.send('exist and ready'.encode())
            wantPeerAddrPortList = [n.addrPort for n in fileDir[wantFilename]]
            peerObj.send(repr(wantPeerAddrPortList).encode())
            print(wantFilename, "peers list have sent...")
            return
        else:
            peerObj.send('not exist'.encode())
            print(wantFilename, "not exit")
            return

if __name__ == '__main__':
    server = socketserver.ThreadingTCPServer(('127.0.0.1',10010), P2Pserver)
    print('P2P sever is running, waiting for connection...')
    server.serve_forever()
