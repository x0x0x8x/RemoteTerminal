import shlex
import socket
import struct
import subprocess
import sys
import threading
import time
import bitarray
import pam
import os
import select
import fcntl
import linuxCommandCompletion
import pty
import shutil

gl_type = 0 #0: normal; 1: http
gl_connected = True
__gl_app_running = False

headTag = b'$:'
__gl_input_queue = []
__gl_output_queue = []

__gl_linuxCmds = []
__gl_curDir = os.getcwd()
__gl_isTop = False
__gl_master_tty = None

def getAppState():
    global __gl_app_running
    return __gl_app_running
def setHttpSshClient(connect = False):
    global gl_connected
    gl_connected = connect

def push_ssh_command(command = b''):
    global __gl_input_queue
    if command == b'':
        return
    __gl_input_queue.append(command)
def pop_ssh_command():
    global __gl_input_queue
    if len(__gl_input_queue) == 0:
        return None
    else:
        return __gl_input_queue.pop(0)
def pop_ssh_command_wait():
    global gl_connected
    cmd = None
    while not cmd and gl_connected:
        cmd = pop_ssh_command()
    return cmd

def push_ssh_response(command = b''):
    global __gl_output_queue
    if command == b'':
        command = b'\0'

    __gl_output_queue.append(command)
def pop_ssh_response():
    global __gl_output_queue
    if len(__gl_output_queue) == 0:
        return None
    else:
        return __gl_output_queue.pop(0)
def ssh_queue_clean():
    global __gl_output_queue
    global __gl_input_queue
    __gl_output_queue.clear()
    __gl_input_queue.clear()


def getCurDir():
    global __gl_curDir
    return __gl_curDir
def setCurDir(dir):
    global __gl_curDir
    print('set curDir: ' + dir)
    __gl_curDir = dir
def isAppAlive(app):
    if './' in app:
        app = app[:-2]
    out = shellIn('top ' + ' | grep ' + app)
    if out == '' or out == None:
        return False
    else:
        return True

def viewAppOutputThread(app):
    time.sleep(2)
    print('viewAppOutputThread >>>')
    while isAppAlive(app):
        try:
            print('read line: ', end='')
            os.system(app + ' > /dev/tty')
            out = sys.stdout.readline()
            print(out)
            client_socket.send((out.encode() + headTag))
        except Exception as e:
            print('error')
            client_socket.send((e + headTag))
            break
    print('viewAppOutputThread <<<')
def recvScanThread(socketfd):
    global gl_connected
    print('recving...')
    while gl_connected:
        data = recvClientMessage(socketfd)
        if data == b'':
            gl_connected = False
            socketfd.close()
            break
        if data:
            #print(f'new cmd: {data}')
            push_ssh_command(data)
    print('recv thread stop')
def responseScanThread(socketfd):
    global gl_connected
    print('resping...')
    try:
        while gl_connected:
            data = pop_ssh_response()
            if data:
                print(f'resp: {data}')
                sendResponse(socketfd, data)

    except Exception as e:
        print(f'resp thread error: {e}')
    print('resp thread stop')

def start_server(host='127.0.0.1', port=2053):
    global __gl_linuxCmds
    global gl_connected

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)

    print(f"ssh server Listening on {host}:{port}")
    #__gl_linuxCmds = linuxCommandCompletion.list_all_commands()

    while True:
        client_socket, addr = server_socket.accept()
        gl_connected = True
        tInput = threading.Thread(target=recvScanThread,args=[client_socket])
        tOutput = threading.Thread(target=responseScanThread, args=[client_socket])
        tInput.start()
        tOutput.start()
        print(f"Connection from {addr}")
        handle_client(client_socket)
        gl_connected = False
        tInput.join()
        tOutput.join()

        ssh_queue_clean()
        gl_connected = True
        print(f"Client disconnect")
        print('free threads')
def start_server_by_other_queue():
    global gl_connected

    client_socket = None
    print('ssh server start....')
    gl_connected = True
    pattern = b"""
            ********************************************************************
              AAA   hh         ooo    nn   nn  gggggg       SSSSS  SSSSS  H   H
             A   A  hh        o   o   nnn  nn gg            S      S      H   H
             AAAAA  hhhhhh    o   o   nn n nn gg  ggg       SSSSS  SSSSS  HHHHH
             A   A  hh   h    o   o   nn  nnn gg   gg           S      S  H   H
             A   A  hh   hhh   ooo    nn   nn  gggggg       SSSSS  SSSSS  H   H
            ********************************************************************
            """
    push_ssh_response(pattern)
    sendCurDirItems(client_socket)

    while gl_connected:
        try:
            command = pop_ssh_command_wait()
            if not command:
                continue
            command = command.decode()
            if command == '':
                break
            if command.lower() in ['exit', 'quit']:
                break
            print('cmd: ' + command)
            output = execute_command(command, client_socket)

            push_ssh_response(output)


        except Exception as e:
            print(f'ssh server Exception error: {e}')
            break
    ssh_queue_clean()
    print(f"ssh server stop...")

def sendResponse(client_socket, str):
    global gl_type
    if gl_type == 0:    # normal keel-alive tcp
        try:
            strLen = len(str).to_bytes(8, 'big')
            #print(f'send {str}({strLen})')
            client_socket.send(strLen)
            client_socket.send(str)
            #print('<<< response done')
        except Exception as e:
            #print(f'send response error: {e}')
            client_socket.close()
    elif gl_type == 1:  #http
        push_ssh_response(str)
    else:
        print(f'invalid gl_type')
        exit(-1)
def recvWaitAll(socketfd, size):
    data = b''
    remainSize = size
    try:
        while remainSize > 0:
            cur = socketfd.recv(remainSize)
            print(cur)
            if cur == b'':
                return b''
            data += cur
            remainSize -= len(cur)
    except Exception as e:
        print('recv wait all error:' + e)
        socketfd.close()
    return data
def recvClientMessage(client_socket):
    global gl_type
    if gl_type == 0:
        try:
            dataLenBytes = recvWaitAll(client_socket,8)
            if dataLenBytes == b'':
                return b''
            dataLen = int.from_bytes(dataLenBytes, 'big')
            data = recvWaitAll(client_socket, dataLen)
            if data == b'':
                return b''
            print(f'command<<<{data}')
            return data
        except Exception as e:
            print(e)
            client_socket.close()
            return None
    elif gl_type == 1:
        return pop_ssh_command()
    else:
        print('invalid gl_type')
        exit(-1)
def handle_client(client_socket):
    # 用户身份验证
    global gl_connected

    try:
        #client_socket.send(b'Username: ')
        #username = client_socket.recv(1024).decode().strip()

        #client_socket.send(b'Password: ')
        #password = client_socket.recv(1024).decode().strip()
        
        #if authenticate(username, password):
        pattern = b"""
        ********************************************************************
          AAA   hh         ooo    nn   nn  gggggg       SSSSS  SSSSS  H   H
         A   A  hh        o   o   nnn  nn gg            S      S      H   H
         AAAAA  hhhhhh    o   o   nn n nn gg  ggg       SSSSS  SSSSS  HHHHH
         A   A  hh   h    o   o   nn  nnn gg   gg           S      S  H   H
         A   A  hh   hhh   ooo    nn   nn  gggggg       SSSSS  SSSSS  H   H
        ********************************************************************
        """

        push_ssh_response(b'Login successful!\n'+pattern+b'\n')

        cmdLen = len((','.join(__gl_linuxCmds)).encode('utf-8'))
        print(f'cmd byte len:{cmdLen}')
        sendCurDirItems(client_socket)
        while gl_connected:
            try:
                command = pop_ssh_command()

                if command == None:
                    continue
                command = command.decode()
                if command == '':
                    print(f"Client disconnect")
                    client_socket.close()
                    return
                if command.lower() in ['exit', 'quit']:
                    break
                print('cmd: '+command)
                output = execute_command(command,client_socket)
                #print('ssh return>>>>> :', end='')
                #print(output)
                push_ssh_response(output)
                #print(f'response : [{output}]')
                #else:
                #    #print('no data')
                #    pass
            except socket.error as e:
                print(f'handle_client error: {e}')
                client_socket.close()
                return
            except Exception as e:
                print(f'handle_client Exception error: {e}')
                client_socket.close()
                return
            
        #else:
            #client_socket.send(b'Login failed!\n')
    except socket.error as e:
        print(f"Send failed: {e}")
    finally:
        client_socket.close()
        return
    client_socket.close()
def authenticate(username, password):
    #pam_auth = pam.authenticate()
    return pam.authenticate(username, password)
def runAppStdinThread(proc, client_socket):
    global __gl_isTop
    global __gl_master_tty
    print('stdin running...')
    try:
        if __gl_isTop:
            while proc.poll() is None:
                reads, writes,excepts = select.select([client_socket],[],[],0.1)
                #print('select')
                if client_socket in reads:
                    #msgIn = recvClientMessage(client_socket)
                    msgIn = pop_ssh_command()
                    if msgIn == None:
                        continue
                    if not msgIn:
                        break
                    if msgIn != b'':
                        #print(f'stdin:[{msgIn}]')
                        os.write(__gl_master_tty, msgIn)

                        #proc.stdin.write(msgIn + b'\r\n')
                        #proc.stdin.flush()
        else:
            while proc.poll() is None:
                reads, writes,excepts = select.select([client_socket],[],[],0.1)
                #print('select')
                if client_socket in reads:
                    #msgIn = recvClientMessage(client_socket)
                    msgIn = pop_ssh_command()
                    if msgIn == None:
                        continue
                    if not msgIn:
                        break
                    if msgIn != b'':
                        #print(f'stdin:[{msgIn}]')
                        proc.stdin.write(msgIn + b'\r\n')
                        proc.stdin.flush()
    except Exception as e:
        proc.terminate()
        print(e)
    print('stdin stop...')
def runAppStdoutThread(proc,client_socket):
    global __gl_isTop
    global __gl_master_tty
    print('stdout running...')
    try:
        if __gl_isTop:
            while proc.poll() is None:
                stdoutLine = os.read(__gl_master_tty, 1024)
                if stdoutLine == b'' or stdoutLine == None:
                    continue
                print(stdoutLine)
                #sendResponse(client_socket, stdoutLine)
                push_ssh_response(stdoutLine)
        else:
            while proc.poll() is None:
                stdoutLine = proc.stdout.readline()
                #stdoutLine = stdoutLine.rstrip()
                if stdoutLine == b'' or stdoutLine == None:
                    continue
                print(stdoutLine)
                #sendResponse(client_socket, stdoutLine)
                push_ssh_response(stdoutLine)
    except subprocess.CalledProcessError as e:
        print(e)
        proc.terminate()
        pass
    except Exception as e:
        print(e)
        proc.terminate()
        pass
    print('stdout stop...')
def runAppSlaveInThread(process, slave, client_socket):
    print('slave in running...')

    try:
        while process.poll() is None:
            cmd = pop_ssh_command_wait()
            if cmd == b'\x03':
                print('*** client ctrl-c ***')
                break
            if cmd != b'':
                print('write ' + cmd.decode())
                if cmd[len(cmd) - 1] != b'\n':
                    cmd += b'\n'
                os.write(slave, cmd)

            '''reads, writes, excepts = select.select([client_socket],[],[],0.1)
            if client_socket in reads:
                #msgIn = recvClientMessage(client_socket)
                msgIn = pop_ssh_command()
                if msgIn == None:
                    continue
                if not msgIn:
                    break
                elif msgIn == b'\x03':
                    print('*** client ctrl-c ***')
                    break
                if msgIn != b'':
                    print('write ' + msgIn.decode())
                    if msgIn[len(msgIn)-1] !=b'\n':
                        msgIn += b'\n'
                    os.write(slave, msgIn)'''

    except Exception as e:
        os.close(slave)
        process.terminate()
        print(e)
    print('slave in stop...')
    process.terminate()
def runAppSlaveOutThread(process, slave, client_socket):
    print('slave out running...')
    cnt = 0
    try:
        while process.poll() is None:
            #print(f'reading [{cnt}]')
            #cnt+=1
            reads, writes, errors = select.select([slave], [slave], [slave],0.1)

            if slave in reads:
                stdoutLine = os.read(slave, 1024)
                if stdoutLine == b'' or stdoutLine == None:
                    continue
                print(f'>>> [{stdoutLine}]')
                #sendResponse(client_socket, stdoutLine)
                push_ssh_response(stdoutLine)
        reads, writes, errors = select.select([slave], [slave], [slave], 0.1)
        if slave in reads:
            stdoutLine = os.read(slave, 1024)
            if stdoutLine != b'' and stdoutLine != None:
                print(f'>>> [{stdoutLine}]')
                #sendResponse(client_socket, stdoutLine)
                push_ssh_response(stdoutLine)

    except subprocess.CalledProcessError as e:
        print(f'slave out error: [{e}]')
        process.terminate()
        pass
    except Exception as e:
        print(f'slave out error: [{e}]')
        process.terminate()
        pass
    print('slave out stop...')
    process.terminate()
def setSlaveNoneBlock(slave):
    flags = fcntl.fcntl(slave, fcntl.F_GETFL)
    fcntl.fcntl(slave, fcntl.F_SETFL, flags | os.O_NONBLOCK)
def setSlaveBlock(slave):
    flags = fcntl.fcntl(slave, fcntl.F_GETFL)
    fcntl.fcntl(slave, fcntl.F_SETFL, flags & ~os.O_NONBLOCK)
def setStdoutNoneBlock(proc):
    fd = proc.stdout.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
def setStdinNoneBlock(proc):
    fd = proc.stdin.fileno()
    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
def runApp(command,client_socket):
    global __gl_isTop
    global __gl_master_tty
    print('run app entry')
    return_code = ''

    try:
        master, slave = pty.openpty()
        master2, slave2 = pty.openpty()
        #'stdbuf -o0 ' +
        proc = subprocess.Popen(command, stdin=slave2, stdout=slave, stderr=slave, shell=True)
        setSlaveNoneBlock(master)

        appOut = threading.Thread(target=runAppSlaveOutThread,args=[proc, master, client_socket])
        appIn = threading.Thread(target=runAppSlaveInThread,args=[proc, master2, client_socket])
        appOut.start()
        appIn.start()

        appOut.join()
        appIn.join()
    except Exception as e:
        print(f'run app error: {e}')
    os.close(slave)
    os.close(master)
    os.close(slave2)
    os.close(master2)
    print('app close')
    proc.terminate()
    print('wait app kill')
    return_code = proc.wait()
    print('app killed')
    print(f"Process finished with return code {return_code}")
    __gl_isTop = False
    return f"Process finished with return code {return_code}"
def cmd_cd_Handle(command):
    if command[:3] == 'cd ':
        path = command[3:]
    elif command[:8] == 'sudo cd ':
        path = command[8:]
    try:
        print('path:' + path)
        os.chdir(path)
        curDir = subprocess.check_output('pwd', shell=True, stderr=subprocess.STDOUT)
        print(curDir)
        setCurDir((curDir.decode()).rstrip())
        return curDir
    except OSError as e:
        return str(e).encode()
    except Exception as e:
        return str(e).encode()
def getDirItemsType(dirItems = []):
    if dirItems == []:
        print('none items')
        return []
    typeList = []
    for item in dirItems:
        itemPath = getCurDir() + '/' + item
        if os.path.isdir(itemPath):
            typeList.append(1)
        elif os.path.isfile(itemPath):
            if os.access(itemPath,os.X_OK):
                typeList.append(3)
            else:
                typeList.append(2)
        else:
            typeList = []
            print(f'invalid dir item type:[{itemPath}]')
            break

    return typeList
def uint8ListToByteArray(num_list = []):
    if num_list == []:
        return b''
    byteArr = struct.pack(f'{len(num_list)}B', *num_list)
    return byteArr
def byteArrayToUint8List(arr = b''):
    if arr == b'':
        return []
    u8list = list(struct.unpack(f'{len(arr)}B', arr))
    return u8list
def sendCurDirItems(socketfd):
    curDirItemList = linuxCommandCompletion.list_all_dir_item(getCurDir())
    cur_dir_items = ','.join(curDirItemList)
    #print('send curDirItems:',end='')
    #print(cur_dir_items)
    #sendResponse(socketfd, cur_dir_items.encode('utf-8'))
    push_ssh_response(cur_dir_items.encode('utf-8'))
    dirItemTypes = getDirItemsType(curDirItemList)
    dirItemTypesList = uint8ListToByteArray(dirItemTypes)
    #sendResponse(socketfd, dirItemTypesList)
    push_ssh_response(dirItemTypesList)
def isApplication(appName):
    if appName[:4] == 'sudo ':
        appName = appName[4:]
    tmp = appName.split('./')
    tmp = (''.join(tmp)).split(' ')
    print(f'>>>> {tmp}')
    path = shutil.which(tmp[0])
    if path:
        return True
    else:
        return False
def execute_command(command,client_socket):
    global __gl_app_running
    try:
        isValidApp = isApplication(command)
        # 执行命令并捕获输出
        if command[:3] == 'cd ' or command[:8] == 'sudo cd ':
            output = cmd_cd_Handle(command)
            if b'[Errno' in output:
                return output
            else:
                push_ssh_response(b'is new dir')
                sendCurDirItems(client_socket)
        elif command[:2] == 'ls' or command[:7] == 'sudo ls':
            #sendResponse(client_socket, b'is new dir')
            push_ssh_response(b'is new dir')
            output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)
            sendCurDirItems(client_socket)
        elif command[:2] == './' or command[:7] == 'sudo ./'\
                or isValidApp:
            #sendResponse(client_socket,b'is valid app')
            push_ssh_response(b'is valid app')
            __gl_app_running = True
            appRet = runApp(command,client_socket)
            __gl_app_running = False
            output = appRet.encode()
        else:
            output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT)

        return output
    except subprocess.CalledProcessError as e:
        return e.output
    except Exception as e:
        return str(e).encode()
if __name__ == "__main__":
    if len(sys.argv) == 1:
        start_server()
    elif len(sys.argv) == 2:
        print('invalid args')
        exit(-1)
    else:
        ip = sys.argv[1]
        port = int(sys.argv[2])
        start_server(ip, port)

