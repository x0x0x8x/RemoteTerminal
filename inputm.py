import sys
import threading
import time
import tty
import termios
import fcntl
import os
import signal

__gl_tabSpaceCnt = 0
__gl_old_settings = None
__gl_fd = -1
__gl_keepRead = True

def getKeepState():
    global __gl_keepRead
    return __gl_keepRead
def setKeepState(keep):
    global __gl_keepRead
    #print(f"set input keep:{keep}")
    __gl_keepRead = keep

def __default_ctrl_c_signal_handle(sig, frame):
    print('ctrl_c_signal_handle')
    exit(0)
def __default_ctrl_z_signal_handle(sig, frame):
    print('ctrl_z_signal_handle')
    exit(0)

def __get_tab_space_count():
    # 使用 Unix/Linux 系统的 stty 命令来获取制表符展开为的空格数量
    # 这里假设终端的设置信息中有关制表符的展开规则
    try:
        output = os.popen('stty -a').read()
        index = output.find('tab')
        if index != -1:
            # 获取 tab=8
            tabNumCh = output[index + 3]
            if tabNumCh == '0':
                num_spaces = 8
            elif num_spaces == '1':
                num_spaces = 4
            else:
                print(f'invalid tab info, num of spaces will be default(8)')
                num_spaces = 8
        else:
            num_spaces = 8
    except ValueError as e:
        print(e)
        num_spaces = 8
    except Exception as e:
        print(e)
        num_spaces = 8

    return num_spaces


def resetOldSetting():
    global __gl_fd
    global __gl_old_settings
    #print('reset old setting')
    if __gl_fd != -1 and __gl_old_settings != None:
        #print('<<<')
        termios.tcsetattr(__gl_fd, termios.TCSADRAIN, __gl_old_settings)
        __gl_fd = -1
        __gl_old_settings = None
def __read_single_keypress():
    global __gl_old_settings
    global __gl_fd

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    __gl_fd = fd
    __gl_old_settings = old_settings

    try:
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)
        #tty.setraw(fd)#造成光标后移？？？
        tty.setcbreak(fd)
        ch = ''
        while ch == '':
            if getKeepState() == False:
                #print('keep is false')
                ch = None
                break
            ch = sys.stdin.readline()
    except Exception as e:
        print(e)
        exit()
    except KeyboardInterrupt as e:
        print(f'KeyboardInterrupt error: {e}')#will active hear when in main thread
        resetOldSetting()
        return '\x03'
    finally:
        resetOldSetting()
    resetOldSetting()

    return ch
def __check_special_keys(key):
    print(f'>>>>[{key.encode()}]')
    if key == '\t':  # Tab
        return "Tab"
    elif key == '\r' or key == '\n':  # Enter
        return "Enter"
    elif key == '\x08' or key == '\x7f':  # Delete (Backspace)
        return "Delete"
    elif key == '\x1b[A':
        return 'UP'
    elif key == '\x03':  # Ctrl + C
        return "Ctrl + C"
    elif key == '\x04':  # Ctrl + D
        return "Ctrl + D"
    elif key == '\x1a':  # Ctrl + Z
        return "Ctrl + Z"
    elif key == '\x01':  # Ctrl + A
        return "Ctrl + A"
    elif key == '\x02':  # Ctrl + B
        return "Ctrl + B"
    elif key == '\x05':  # Ctrl + E
        return "Ctrl + E"
    elif key == '\x06':  # Ctrl + F
        return "Ctrl + F"
    elif key == '\x09':  # Ctrl + I (Tab)
        return "Ctrl + I (Tab)"
    elif key == '\x0b':  # Ctrl + K
        return "Ctrl + K"
    elif key == '\x0c':  # Ctrl + L
        return "Ctrl + L"
    elif key == '\x10':  # Ctrl + P
        return "Ctrl + P"
    elif key == '\x11':  # Ctrl + Q
        return "Ctrl + Q"
    elif key == '\x12':  # Ctrl + R
        return "Ctrl + R"
    elif key == '\x13':  # Ctrl + S
        return "Ctrl + S"
    elif key == '\x14':  # Ctrl + T
        return "Ctrl + T"
    elif key == '\x17':  # Ctrl + W
        return "Ctrl + W"
    elif key == '\x18':  # Ctrl + X
        return "Ctrl + X"
    elif key == '\x19':  # Ctrl + Y
        return "Ctrl + Y"
    elif key == '\x1a':  # Ctrl + Z
        return "Ctrl + Z"
    else:
        return key
def __handle_backspace(input_buffer):
    global __gl_tabSpaceCnt
    if input_buffer:
        ch = input_buffer.pop()
        # Move cursor back, overwrite with space, move cursor back again
        if ch == '\t':
            sys.stdout.write('\r')
            sys.stdout.write(''.join(input_buffer))
            sys.stdout.flush()
        else:
            sys.stdout.write('\b \b')
            sys.stdout.flush()
def __defaultKeyHandle():
    input_buffer = []
    try:
        while getKeepState():
            key = __read_single_keypress()
            if key == None:
                resetOldSetting()
                break
            #print(key.encode())
            if key == '\t':  # Tab
                input_buffer.append('\t')
                sys.stdout.write('\t')
                sys.stdout.flush()
            elif key == '\r' or key == '\n':  # Enter
                # print(''.join(input_buffer))
                ret = ''.join(input_buffer)
                input_buffer.clear()
                print()
                return ret
            elif key == '\x08' or key == '\x7f':  # Delete (Backspace)
                __handle_backspace(input_buffer)
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
def __main(key_handle = None):
    #print("Press any key (Ctrl+C to exit):")

    if key_handle:
        print('key handle exists')
        return key_handle()
    else:
        return __defautKeyHandle()

def inputm():
    return __main()

def appendInputBuffer(str):
    global gl_input_buffer
    gl_input_buffer.append(str)
    sys.stdout.write(str)
    sys.stdout.flush()

def inputSSH(key_handle = None,
                              sigintHandle = None,
                              sigtstpHandle = None):
    sys.stdout.flush()
    return activeInputBySignalHandle(key_handle, sigintHandle, sigtstpHandle)

def activeInputBySignalHandle(key_handle = None,
                              sigintHandle = None,
                              sigtstpHandle = None):
    # print("Press any key (Ctrl+C to exit):")
    if sigintHandle:
        signal.signal(signal.SIGINT,sigintHandle)
    if sigtstpHandle:
        signal.signal(signal.SIGTSTP,sigtstpHandle)

    if key_handle:
        #print('key handle exists')
        return key_handle()
    else:
        return __defaultKeyHandle()


if __name__ == "__main__":
    str = activeInputBySignalHandle(sigintHandle=__default_ctrl_c_signal_handle,
                                    sigtstpHandle=__default_ctrl_z_signal_handle)
