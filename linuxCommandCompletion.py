import os
import subprocess

def get_executable_files(path):
    try:
        files = os.listdir(path)
        #print(files)
        executables = []
        #cnt = 1
        for file in files:
            full_path = os.path.join(path, file)
            if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                #print(f'[{len(files)}] {cnt}')
                #cnt+=1
                executables.append(file)
        return executables
    except FileNotFoundError:
        return []
def list_all_commands():
    # 获取系统中的所有可执行文件路径
    executable_files = []

    # 遍历系统环境变量中的所有路径
    for path in os.environ["PATH"].split(os.pathsep):
        try:
            # 获取该路径下的所有文件和文件夹
            files = os.listdir(path)
            for file in files:
                file_path = os.path.join(path, file)
                # 检查文件是否可执行
                if os.access(file_path, os.X_OK) and os.path.isfile(file_path) and '.' not in file_path:
                    tmp = file_path.split('/')
                    executable_files.append(tmp[len(tmp)-1])
        except OSError:
            continue

    print(executable_files)
    return executable_files


    paths = os.environ.get('PATH', '').split(os.pathsep)
    all_commands = set()
    for path in paths:
        commands = get_executable_files(path)
        all_commands.update(commands)
    return sorted(all_commands)

def list_all_dir_item(dir):
    all_items = os.listdir(dir)
    return all_items

if __name__ == "__main__":
    commands = list_all_commands()
    print(commands)