可执行文件：
/dist/sshHost
/dist/sshClient

host端开启示例：
./sshHost 127.0.0.1 2052 或 ./sshHost

默认ip和端口为 127.0.0.1:2053

client端开启示例：
./sshClient 127.0.0.1 2052 或 ./sshClient

默认ip和端口为 127.0.0.1:2053

注意！！：
如遇到输入错误，请第一时间按 ctrl+c 退出当前会话，不要胡乱输入，以防勿执行危险命令！


当前支持功能：
基本的linux指令，如ls，cd，top，ifconfig等。
tab补全当前目录文件/文件夹。
上/下键切换历史输入。
左右键切换光标位置，可配合backspace键在中间删除字符或输入新字符。(暂不支持delete键)
自定义程序的交互操作，如scanf输入。


不支持：
vim等文本编辑。
