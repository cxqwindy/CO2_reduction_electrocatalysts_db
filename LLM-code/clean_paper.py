import paramiko
from scp import SCPClient
import json
import stat
import re
import random
import pandas as pd

#服务器信息，主机名（IP地址）、端口号、用户名及密码
hostname = "10.0.87.16"
port = 22
username = "root"
password = "cnic.cn"


def noref(line):
    new_line = re.sub(r'\[\d+(\–\d+)?\]','', line)
    new_line = re.sub(r'\[\d+(\-\d+)?\]','', new_line)
    new_line = re.sub(r'\[\d+(,\d+)*\]','', new_line)
    return new_line
def islegal(line):
    if line[:3] == 'Fig' or line[:3] == 'www' or line[:3] == 'DOI' or '*' in line:
        return False
    if len(line) < 35:
        return False
    if '@' in line or '©' in line or '~' in line:
        return False
    lline = line.split('.')
    for word in lline:
        words = word.split(' ')
        if len(words) == 1 and words[0] != 'i' and words[0] != 'e' and words[0] != 'g' and words[0] != '' and words[0] != '\n':
            pattern = re.compile(r"\d+[\-\–]\d+")
            if not(pattern.search(words[0])):
                #print(line)
                #print(words[0])
                #print('option 4')
                return False
    return True
def merge_paragraph(inputDir, outputDir, remoteFileName):
    with open (outputDir + remoteFileName + '.txt', 'a') as writer:
        with open(inputDir + 'paragraph.txt', 'r') as f:
            line = f.readline()
            next_line = f.readline()
            while(next_line):
                if not next_line[0].isupper(): #如果开头是小写字母，代表上一段落还没结束
                    writer.write(line.strip() + ' ')
                    line = next_line
                else:
                    writer.write(line)
                    line = next_line
                next_line = f.readline()
            writer.write(line)


client = paramiko.SSHClient()
#client.load_system_host_keys()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname, port, username, password, compress=True)
sftp_client = client.open_sftp()
remote_file = sftp_client.open("/mnt/ssd2/wld/photocataly_parsed//10.1002/adma.201803569.json")#文件路径
content = remote_file.read()
content_dict = json.loads(content)
#print(content_dict["abstract"])
sections = content_dict["sections"]
#with open('paper_metadata/test.txt', 'w') as writer:
#    for section in sections:
#        writer.write(section['text'])
#        writer.write('\n')
#with open('paper_metadata/test.txt', 'r') as f:
#    with open('paper_metadata/test_1.txt','w') as writer:
#        line = f.readline()
#        while (line):
#            new_line = noref(line)
#            if islegal(new_line):
#                writer.write(new_line)
#            line = f.readline()
#merge_paragraph('paper_metadata/','final_data/','abc')

# 获取transport传输实例, sftp服务器 ip + 端口号
tran = paramiko.Transport(('10.0.87.16', 22))
# 连接ssh服务器, user + password
tran.connect(username='root', password='cnic.cn')
# 获取sftp实例
sftp = paramiko.SFTPClient.from_transport(tran)


def getRemoteFiles(remoteDir):
    # 加载sftp服务器文件对象(根目录)
    filesAttr = sftp.listdir_attr(remoteDir)
    try:
        # foreach遍历
        for fileAttr in filesAttr:
            if stat.S_ISDIR(fileAttr.st_mode):
                # 1.当是文件夹时
                # 计算子文件夹在ftp服务器上的路径
                son_remoteDir = remoteDir + '/' + fileAttr.filename
                # 生成器, 迭代调用函数自身
                yield from getRemoteFiles(son_remoteDir)
            else:
                # 2.当是文件时
                # 生成器, 添加"路径+文件名"到迭代器"
                yield remoteDir + '/' + fileAttr.filename
    except Exception as e:
        print('getAllFilePath exception:', e)


# 远程目录remoteDir文件下载保存到本地目录localDir
def clean_data(remoteDir, middleDir):

    # 实例化生成器, 获取sftp指定目录下的所有文件路径
    files = getRemoteFiles(remoteDir)
    i = 0
    outputDir = 'co2_data/'
    # foreach遍历
    for file in files:
        # 要下载的远程文件, 本地时路径+文件名
        #print(file)
        remoteFileName = (file.split('/')[-2] + '/' + file.split('/')[-1][:-5]).replace('/','_')
        #print(remoteFileName)
        i += 1
        sftp_client = client.open_sftp()
        remote_file = sftp_client.open(file) #文件路径
        content = remote_file.read()
        content_dict = json.loads(content)
        #print(file)
        #print(content_dict["abstract"])
        sections = content_dict["sections"]
        try:
            with open(middleDir + 'test.txt', 'w') as writer:
                #print('section 1')
                #print(i)
                for section in sections: #sections是一个list,section是一个{heading:xxx, text:yyy}的字典
                    for key in section.keys():
                        if section[key] == "Keywords" or section[key] == "Acknowledgements" or section[key] == "Conflict of Interest":
                            break
                        else:
                            writer.write(section['text'])
                            writer.write('\n')
                            break
            with open (middleDir+ 'paragraph.txt', 'w') as writer:
                with open(middleDir + 'test.txt', 'r') as f:
                    #print('section 2')
                    #print(i)
                    line = f.readline()
                    while(line):
                        new_line = noref(line)
                        if islegal(new_line):
                            writer.write(new_line)
                        line = f.readline()
            #print('section 3')
            #print(i)
            merge_paragraph(middleDir, outputDir, remoteFileName)
            print(i)
        except Exception as e:
            print("there is no sections in" + file)

    sftp.close()


#download_file('/opt/mfs/duyi/cataly/photocataly_json/', 'synthesis_data/')
#tc_generation('synthesis_data/')
#download_file('/mnt/ssd2/wld/gold_data/', 'goldcorpus_data/')
#tc_generation('goldcorpus_data/')
clean_data('/mnt/ssd2/wld/co2_data/','paper_metadata/')