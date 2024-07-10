import os
import socket
import threading
import time
import difflib
import inputm
import sys
import struct
import re


gl_handle_type = 0 #0: normal; 1: http
if gl_handle_type == 1:
    import HTTPSClient

user_state = -1
tabEnter = False
keyBoardInput = ''
__gl_keepAppRun = True
__gl_appReturn = ''
__gl_host_socke = None
__gl_historyInputBuffer = []
__gl_input_buffer = []
__gl_linuxCmds = []
__gl_cur_dir_items = []
__gl_cur_dir_items_type = []
__gl_lastStdoutEnterCnt = 0
__gl_headTag = '\033[999;1H' + '$: '

def runAppStdout(client_socket):
    global __gl_input_buffer
    global __gl_appReturn
    global __gl_lastStdoutEnterCnt
    global __gl_keepAppRun
    #print('stdout running...')
    try:
        while __gl_keepAppRun:
            #print('keep recving....')
            dataByte = recvResponse(client_socket)
            #print(dataByte)
            if dataByte:
                data = dataByte.decode()
            else:
                __gl_appReturn = 'Process finished\n'
                break
            if data == '':
                continue
            if 'Process finished' in data:
                __gl_appReturn = data
                break
            print(data, end='')
            #sys.stdout.flush()
    except Exception as e:
        print(f'app running out error: {e}')

    __gl_keepAppRun = False
    inputm.setKeepState(False)
    #print('stdout stop...')
def runAppStdout_http():
    global __gl_input_buffer
    global __gl_appReturn
    global __gl_lastStdoutEnterCnt
    global __gl_keepAppRun
    #print('stdout running...')
    try:
        while __gl_keepAppRun:
            #print('keep recving....')
            dataByte = http_get_resp_wait()
            #print(dataByte)
            if dataByte:
                data = dataByte.decode()
            else:
                __gl_appReturn = 'Process finished\n'
                break
            if data == '':
                continue
            if 'Process finished' in data:
                __gl_appReturn = data
                break
            print(data, end='')
            #sys.stdout.flush()
    except Exception as e:
        print(f'app running out error: {e}')

    __gl_keepAppRun = False
    inputm.setKeepState(False)

def printDirItems():
    #print('*** print dir ***')
    global __gl_cur_dir_items
    global __gl_cur_dir_items_type
    if not __gl_cur_dir_items or not __gl_cur_dir_items_type:
        return
    if len(__gl_cur_dir_items) == 0 or len(__gl_cur_dir_items_type) == 0:
        return

    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

    for i in range(len(__gl_cur_dir_items)):
        if __gl_cur_dir_items_type[i] == 1:
            print(BLUE + __gl_cur_dir_items[i] + RESET + '\t', end='')
        elif __gl_cur_dir_items_type[i] == 3:
            print(GREEN + __gl_cur_dir_items[i] + RESET + '\t', end='')
        else:
            print(__gl_cur_dir_items[i] + '\t', end='')
    print()
def printDirItemsByList(items):
    global __gl_cur_dir_items
    global __gl_cur_dir_items_type
    if not __gl_cur_dir_items or not __gl_cur_dir_items_type:
        return
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

    if items[0] in __gl_cur_dir_items:
        for i in range(len(__gl_cur_dir_items)):
            if __gl_cur_dir_items[i] in items:
                if __gl_cur_dir_items_type[i] == 1:
                    print(BLUE + __gl_cur_dir_items[i] + RESET + '\t', end='')
                elif __gl_cur_dir_items_type[i] == 3:
                    print(GREEN + __gl_cur_dir_items[i] + RESET + '\t', end='')
                else:
                    print(__gl_cur_dir_items[i] + '\t', end='')
        print()

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

def key_tab_handle(socket):
    #print('tab handle')
    #sendHostMessage(socket, '\t'.encode())
    pass
def backspace_handle(input_buffer, backCnt = 0):
    global __gl_tabSpaceCnt
    if input_buffer:
        if backCnt == 0:
            lastBufferLen = len(input_buffer)
            ch = input_buffer.pop()
            sys.stdout.write(f'\033[{lastBufferLen}D')
            sys.stdout.write(' '*lastBufferLen)
            sys.stdout.write(f'\033[{lastBufferLen}D')
            sys.stdout.write(''.join(input_buffer))
            sys.stdout.flush()

            return 0
        else:
            lastBufferLen = len(input_buffer)
            idx = lastBufferLen - backCnt - 1
            ch = input_buffer.pop(idx)
            sys.stdout.write(f'\033[{idx+1}D')
            sys.stdout.write(' ' * lastBufferLen)
            sys.stdout.write(f'\033[{lastBufferLen}D')
            sys.stdout.write(''.join(input_buffer))
            sys.stdout.write(f'\033[{backCnt}D')
            sys.stdout.flush()

            return backCnt
def inputClear(input_buffer):
    lastBufferLen = len(input_buffer)
    if lastBufferLen > 0:
        #print(f'[{lastBufferLen}]')
        sys.stdout.write(f'\033[{lastBufferLen}D')
        sys.stdout.write(' ' * lastBufferLen)
        sys.stdout.write(f'\033[{lastBufferLen}D')
        sys.stdout.flush()
def sshClientKeyHandle():
    global __gl_input_buffer
    input_buffer = __gl_input_buffer
    try:
        while inputm.getKeepState():
            key = inputm.__read_single_keypress()
            if key == None:
                inputm.resetOldSetting()
                break
            if key == '\t':  # Tab
                input_buffer.append('\t')
                sys.stdout.write('\t')
                sys.stdout.flush()
            elif key == '\r' or key == '\n':  # Enter
                ret = ''.join(input_buffer)
                input_buffer.clear()
                __gl_input_buffer.clear()
                print()
                return ret
            elif key == '\x08' or key == '\x7f':  # Delete (Backspace)
                inputm.__handle_backspace(input_buffer)
                pass
            elif key == '\x1b[A':
                print('UP')
            elif key == '\x1b[B':
                print('DOWN')
            elif key == '\x1b[D':
                print('LEFT')
            elif key == '\x1b[C':
                print('Right')
            elif key == '\x03':  # Ctrl + C
                print('Ctrl + C')
            elif key == '\x04':  # Ctrl + D
                print('Ctrl + D')
            elif key == '\x1a':  # Ctrl + Z
                print('Ctrl + Z')
            elif key == '\x01':  # Ctrl + A
                print('Ctrl + A')
            elif key == '\x02':  # Ctrl + B
                print('Ctrl + B')
                exit(0)
            elif key == '\x05':  # Ctrl + E
                print('Ctrl + E')
            elif key == '\x06':  # Ctrl + F
                print('Ctrl + F')
            elif key == '\x09':  # Ctrl + I (Tab)
                print('Ctrl + I (Tab)')
            elif key == '\x0b':  # Ctrl + K
                print('Ctrl + K')
            elif key == '\x0c':  # Ctrl + L
                print('Ctrl + L')
            elif key == '\x10':  # Ctrl + P
                print('Ctrl + P')
            elif key == '\x11':  # Ctrl + Q
                print('Ctrl + Q')
            elif key == '\x12':  # Ctrl + R
                print('Ctrl + R')
            elif key == '\x13':  # Ctrl + S
                print('Ctrl + S')
            elif key == '\x14':  # Ctrl + T
                print('Ctrl + T')
            elif key == '\x17':  # Ctrl + W
                print('Ctrl + W')
            elif key == '\x18':  # Ctrl + X
                print('Ctrl + X')
            elif key == '\x19':  # Ctrl + Y
                print('Ctrl + Y')
            elif key == '\x1a':  # Ctrl + Z
                print('Ctrl + Z')
            elif len(key) == 1:
                input_buffer.append(key)
                sys.stdout.write(key)
                sys.stdout.flush()
                # print(key)
            else:
                input_buffer.append(key)
                sys.stdout.write(key)
                sys.stdout.flush()
                # print(key)
                #print('unkown key')
                pass
    except Exception as e:
        print(e)
        exit(-1)

    return None
def sshNormalKeyHandle():
    global __gl_input_buffer
    global __gl_historyInputBuffer
    #print(__gl_historyInputBuffer)
    input_buffer = __gl_input_buffer
    backCnt = 0
    historyIndex = -1
    try:
        while inputm.getKeepState():
            key = inputm.__read_single_keypress()
            if key == None:
                inputm.resetOldSetting()
                break
            #print(key.encode())
            if key == '\t':  # Tab
                key_tab_handle(__gl_host_socke)
                return '\t'
            elif key == '\r' or key == '\n':  # Enter
                # print(''.join(input_buffer))
                ret = ''.join(input_buffer)
                input_buffer.clear()
                __gl_input_buffer.clear()
                #print('\n' + ret + f'[{backCnt}]')
                if ret != '':
                    __gl_historyInputBuffer.insert(0, ret)
                print()
                return ret
            elif key == '\x08' or key == '\x7f':  # Delete (Backspace)
                backCnt = backspace_handle(input_buffer, backCnt)
                pass
            elif key == '\x1b[A':
                #print('UP')
                if historyIndex < len(__gl_historyInputBuffer):
                    if historyIndex < len(__gl_historyInputBuffer) -1:
                        historyIndex += 1

                    inputClear(input_buffer)
                    input_buffer.clear()
                    input_buffer.append(__gl_historyInputBuffer[historyIndex])
                    sys.stdout.write(''.join(input_buffer))
                    sys.stdout.flush()

            elif key == '\x1b[B':
                #print('DOWN')
                if historyIndex >= 0:
                    if historyIndex > 0:
                        historyIndex -= 1
                    inputClear(input_buffer)
                    input_buffer.clear()
                    input_buffer.append(__gl_historyInputBuffer[historyIndex])
                    sys.stdout.write(''.join(input_buffer))
                    sys.stdout.flush()
            elif key == '\x1b[D':
                #print('LEFT')
                sys.stdout.write('\033[1D')
                sys.stdout.flush()
                backCnt += 1
                if backCnt > len(input_buffer):
                    backCnt = len(input_buffer)
            elif key == '\x1b[C':
                #print('Right')
                sys.stdout.write('\033[1C')
                sys.stdout.flush()
                backCnt -= 1
                if backCnt < 0:
                    backCnt = 0
            elif key == '\x03':  # Ctrl + C
                #print('Ctrl + C')
                exit(0)
            elif key == '\x04':  # Ctrl + D
                print('Ctrl + D')
            elif key == '\x1a':  # Ctrl + Z
                print('Ctrl + Z')
            elif key == '\x01':  # Ctrl + A
                print('Ctrl + A')
            elif key == '\x02':  # Ctrl + B
                print('Ctrl + B')
            elif key == '\x05':  # Ctrl + E
                print('Ctrl + E')
            elif key == '\x06':  # Ctrl + F
                print('Ctrl + F')
            elif key == '\x09':  # Ctrl + I (Tab)
                print('Ctrl + I (Tab)')
            elif key == '\x0b':  # Ctrl + K
                print('Ctrl + K')
            elif key == '\x0c':  # Ctrl + L
                print('Ctrl + L')
            elif key == '\x10':  # Ctrl + P
                print('Ctrl + P')
            elif key == '\x11':  # Ctrl + Q
                print('Ctrl + Q')
            elif key == '\x12':  # Ctrl + R
                print('Ctrl + R')
            elif key == '\x13':  # Ctrl + S
                print('Ctrl + S')
            elif key == '\x14':  # Ctrl + T
                print('Ctrl + T')
            elif key == '\x17':  # Ctrl + W
                print('Ctrl + W')
            elif key == '\x18':  # Ctrl + X
                print('Ctrl + X')
            elif key == '\x19':  # Ctrl + Y
                print('Ctrl + Y')
            elif key == '\x1a':  # Ctrl + Z
                print('Ctrl + Z')
            elif len(key) == 1:
                if backCnt > 0:
                    lastBufferLen = len(input_buffer)
                    input_buffer.insert(lastBufferLen - backCnt, key)
                    #input_buffer[len(input_buffer) - backCnt] = key
                    sys.stdout.write(f'\033[{lastBufferLen - backCnt}D')
                    sys.stdout.flush()
                    sys.stdout.write(''.join(input_buffer))
                    sys.stdout.write(f'\033[{backCnt}D')
                    #backCnt -= 1
                else:
                    input_buffer.append(key)
                    sys.stdout.write(key)
                sys.stdout.flush()
                # print(key)
            else:
                print(f'unkown key: {key}({len(key)})')
                pass
    except Exception as e:
        print(e)
        exit(-1)

    return None
def strListToCharList(strList = []):
    if strList == []:
        return []
    ret = []
    for str in strList:
        if len(str) > 1:
            for ch in str:
                ret.append(ch)
        else:
            ret.append(str)
    return ret

def ctrl_c_handle_when_appruning(sig, frame):
    inputm.setKeepState(False)

def ctrl_c_handle_when_normal(sig, frame):
    global __gl_host_socke
    #print('normal sigint handle')
    if __gl_host_socke:
        __gl_host_socke.close()
    if not __gl_host_socke:
        http_sshSendCommandPost(b'\x03')
    inputm.resetOldSetting()
    exit(0)
def runAppStdin(client_socket):
    global __gl_keepAppRun
    global __gl_input_buffer

    try:
        while __gl_keepAppRun:
            str = inputm.inputSSH(key_handle=sshClientKeyHandle, sigintHandle=ctrl_c_handle_when_appruning)
            if not str and not inputm.getKeepState() and __gl_keepAppRun:
                sendHostMessage(client_socket, b'\x03')
                break
            if str == '':
                continue
            if str == None:
                break
            sendHostMessage(client_socket,str.encode())
    except Exception as e:
        print(f'runApp stdin error: {e}')
        pass

    #print('stdin finishing...')
def runAppStdin_http():
    global __gl_keepAppRun
    global __gl_input_buffer

    try:
        while __gl_keepAppRun:
            str = inputm.inputSSH(key_handle=sshClientKeyHandle, sigintHandle=ctrl_c_handle_when_appruning)
            if not str and not inputm.getKeepState() and __gl_keepAppRun:
                http_sshSendCommandPost(b'\x03')
                break
            if str == '':
                continue
            if str == None:
                break
            http_sshSendCommandPost(str.encode())
    except Exception as e:
        print(f'runApp stdin http error: {e}')
        pass
def runApp(client_socket):
    global __gl_appReturn
    global __gl_keepAppRun
    __gl_keepAppRun = True
    inputm.setKeepState(True)
    try:
        appOut = threading.Thread(target=runAppStdout, args=[client_socket])
        appOut.start()
        runAppStdin(client_socket)
        appOut.join()
        inputm.setKeepState(True)
        return __gl_appReturn
    except Exception as e:
        print(f'runApp error: {e}')
        inputm.setKeepState(True)
        return None
def runApp_http():
    global __gl_appReturn
    global __gl_keepAppRun
    __gl_keepAppRun = True
    inputm.setKeepState(True)
    try:
        appOut = threading.Thread(target=runAppStdout_http)
        appOut.start()
        runAppStdin_http()
        appOut.join()

        inputm.setKeepState(True)
        return __gl_appReturn
    except Exception as e:
        print(f'runApp http error: {e}')
        inputm.setKeepState(True)
        return None
def recvWaitAll(socketfd, size):
    data = b''
    remainSize = size
    try:
        while remainSize > 0:
            cur = socketfd.recv(remainSize)
            data += cur
            remainSize -= len(cur)
    except Exception as e:
        print('recv wait all error:' + e)
        socketfd.close()
    return data
def recvResponse(client_socket):
    try:
        lenByte = recvWaitAll(client_socket,8)
        strLen = int.from_bytes(lenByte, 'big')
        #print(f'recv len = {strLen}')
        data = recvWaitAll(client_socket, strLen)
        #print(f'recv<<<{data}')
        return data
    except Exception as e:
        print(e)
        client_socket.close()
        return None
def sendHostMessage(client_socket, str):
    try:
        #print(f'send>>>[{len(str)}][{str}]')
        strLen = len(str).to_bytes(8, 'big')
        client_socket.send(strLen)
        client_socket.send(str)
    except Exception as e:
        print(e)
        client_socket.close()
def recvCurDirItems(client_socket):
    curDir = recvResponse(client_socket)
    curDirTypes = recvResponse(client_socket)
    curDirTypesList = byteArrayToUint8List(curDirTypes)
    return (curDir.decode('utf-8')).split(','), curDirTypesList
def recvCurDirItems_http():
    curDir = http_get_resp_wait()
    curDirTypes = http_get_resp_wait()
    curDirTypesList = byteArrayToUint8List(curDirTypes)
    return (curDir.decode('utf-8')).split(','), curDirTypesList
def matchComplete(input_buffer = [], items=[], itemsType = []):
    global __gl_headTag
    if input_buffer == [] or items == [] or itemsType == []:
        print('invalid input')
        return
    curStr = ''.join(input_buffer)
    commandArr = []
    realCommand = ''.join(input_buffer)
    realCommand = re.split(f'({re.escape("./")})', realCommand)
    commandArr += realCommand
    realCommand = realCommand[len(realCommand) - 1]
    commandArr.remove(realCommand)

    realCommand = re.split(f'({re.escape(" ")})', realCommand)
    commandArr += realCommand
    realCommand = realCommand[len(realCommand) - 1]
    commandArr.remove(realCommand)

    commandArr = strListToCharList(commandArr)

    matches = [itemlist for itemlist in items if itemlist.startswith(realCommand)]
    # print(matches)
    if len(matches) == 0 or realCommand == '':
        pass
    elif len(matches) == 1:
        input_buffer.clear()
        arr = commandArr + list(matches[0])
        for i in range(len(arr)):
            input_buffer.append(arr[i])
        #print(len(input_buffer))
        #print(input_buffer)
        sys.stdout.write('\r\033[2K' + __gl_headTag)
        sys.stdout.write(''.join(commandArr) + matches[0])
        sys.stdout.flush()
    else:
        sys.stdout.write('\r\033[2K')
        #sys.stdout.flush()
        printDirItemsByList(matches)
        print(__gl_headTag + curStr, end='')

    return
def connect_to_server(host='127.0.0.1', port=2222):
    global user_state
    global tabEnter
    global __gl_input_buffer
    global __gl_host_socke
    global __gl_linuxCmds
    global __gl_cur_dir_items
    global __gl_cur_dir_items_type
    headTag = '\033[999;1H' + '$: '

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    __gl_host_socke = client_socket
    data = recvResponse(client_socket).decode()

    __gl_cur_dir_items, __gl_cur_dir_items_type = recvCurDirItems(client_socket)
    print(data, end='')

    isTab = False
    while True:
        try:
            if not isTab:
                print(headTag,end='')
            else:
                isTab = False
            command = inputm.inputSSH(key_handle=sshNormalKeyHandle, sigintHandle=ctrl_c_handle_when_normal)
            #print(command)
            if command.lower() in ['exit', 'quit'] or command == 'Ctrl + C':
                client_socket.close()
                exit(0)
            elif command == '':
                continue
            elif command == '\t':
                isTab = True
                matchComplete(__gl_input_buffer, __gl_cur_dir_items, __gl_cur_dir_items_type)
                continue
            if not checkSupportCommand(command):
                print('Unsupported command')
                continue

            sendHostMessage(client_socket, command.encode())
            resp = recvResponse(client_socket).decode()

            if 'is valid app' in resp:
                resp = runApp(client_socket)
                #if '\n' in resp:
                #    print(resp,end='')
                #else:
                #    print(resp)
            elif 'is new dir' in resp:
                __gl_cur_dir_items, __gl_cur_dir_items_type = recvCurDirItems(client_socket)
                resp = recvResponse(client_socket).decode()
                # print(__gl_cur_dir_items)
                printDirItems()
            else:
                print(resp)

        except socket.error as e:
            print(f'error: {e}')
            client_socket.close()
            exit(0)
        except Exception as e:
            print(f'error: {e}')
            client_socket.close()
            exit(0)
    client_socket.close()


def http_sshSendCommandPost(command = b''):
    ip = '127.0.0.1'
    port = 8000
    url = f'http://{ip}:{port}/PhotoGallery/UploadImg'

    return HTTPSClient.postMsgToHost(url=url, ip=ip,port=port,data=(b'1' + b'1' + command))
def http_getResponseFromSshHost():
    ip = '127.0.0.1'
    port = 8000
    url = f'http://{ip}:{port}/PhotoGallery/UploadImg'

    return HTTPSClient.postMsgToHost(url=url, ip=ip, port=port, data=(b'1' + b'2'))
def http_login():
    ip = '127.0.0.1'
    port = 8000
    url = f'http://{ip}:{port}/PhotoGallery/UploadImg'

    return HTTPSClient.postMsgToHost(url=url, ip=ip, port=port, data=(b'1' + b'0'))
def http_get_resp_wait():
    resp = b'\1'
    while not resp or resp == b'\1':
        resp = http_getResponseFromSshHost()
        #time.sleep(0.5)
    return resp
def checkSupportCommand(command = ''):
    unsupportList = ['vim', 'sudo vim', 'vi', 'sudo vi']
    if command in unsupportList:
        return False
    else:
        return True
def connect_to_http_server(host='127.0.0.1', port=2052):
    global __gl_cur_dir_items
    global __gl_cur_dir_items_type
    global __gl_headTag

    loginMsg = http_login()
    if loginMsg != b'\1':
        print('login fail')
        return
    else:
        print('Login success')
    loginMsg = http_get_resp_wait()
    __gl_cur_dir_items, __gl_cur_dir_items_type = recvCurDirItems_http()

    print(loginMsg.decode())
    isTab = False
    while True:
        try:
            if not isTab:
                print(__gl_headTag, end='')
            else:
                isTab = False
            command = inputm.inputSSH(key_handle=sshNormalKeyHandle, sigintHandle=ctrl_c_handle_when_normal)
            # print(command)
            if command.lower() in ['exit', 'quit'] or command == 'Ctrl + C':
                http_sshSendCommandPost(b'\x03')
                exit(0)
            elif command == '':
                continue
            elif command == '\t':
                isTab = True
                matchComplete(__gl_input_buffer, __gl_cur_dir_items, __gl_cur_dir_items_type)
                continue
            if not checkSupportCommand(command):
                print('Unsupported command')
                continue

            resp = http_sshSendCommandPost(command.encode())
            resp = http_get_resp_wait().decode()

            if 'is valid app' in resp:
                resp = runApp_http()
                #if '\n' in resp:
                #    print(resp, end='')
                #else:
                #    print(resp)
            elif 'is new dir' in resp:
                __gl_cur_dir_items, __gl_cur_dir_items_type = recvCurDirItems_http()
                resp = http_get_resp_wait().decode()
                # print(__gl_cur_dir_items)
                printDirItems()
            else:
                print(resp)
        except Exception as e:
            print(f'error: {e}')
            http_sshSendCommandPost(b'\x03')
            exit(0)
    http_sshSendCommandPost(b'\x03')

if __name__ == "__main__":

    if len(sys.argv) == 1:
        while True:
            if gl_handle_type == 0:
                connect_to_server('127.0.0.1',2053)
            else:
                connect_to_http_server('127.0.0.1',2053)
    elif len(sys.argv) == 3:
        ip = sys.argv[1]
        port = int(sys.argv[2])
        while True:
            if gl_handle_type == 0:
                connect_to_server(ip, port)
            else:
                connect_to_http_server(ip, port)
    else:
        print('invalid args')
        exit(-1)