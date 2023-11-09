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


client = paramiko.SSHClient()
#client.load_system_host_keys()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(hostname, port, username, password, compress=True)
sftp_client = client.open_sftp()
remote_file = sftp_client.open("/mnt/ssd2/wld/gold_data//10.1002/adfm.201910118.json")#文件路径
content = remote_file.read()
content_dict = json.loads(content)
print(content_dict["abstract"])
sections = content_dict["sections"]
with open('goldcorpus_data/reference.txt', 'w') as writer:
    for section in sections:
        for key in section.keys():
            #print(key)
            if section[key] == "Keywords":
                writer.write(section['text'])
                writer.write('\n')
                break
#with open('goldcorpus_data/test.txt', 'w') as writer:
    #for section in sections:
        #for key in section.keys():
            #print(key)
            #if section[key] == "Keywords":
                #print('ahhhh')
                #break
            #else:
                #writer.write(section['text'])
                #writer.write('\n')
                #break

#num = []
#with open ('synthesis_data/test_3.txt', 'w') as writer:
#    with open('synthesis_data/test.txt', 'r') as f:
#        line = f.readline()
#        next_line = f.readline()
#        while(next_line):
#            if len(next_line) < 35 or next_line[:3] == 'Fig':
#                next_line = f.readline()
#            else:
#                if not next_line[0].isupper(): #如果开头是小写字母，代表上一段落还没结束
#                    writer.write(line.strip() + ' ')
#                    line = next_line
#                else:
#                    writer.write(line)
#                    line = next_line
                #num.append(len(line))
#                next_line = f.readline()
#        writer.write(line)
#print(num)


#try:
#  for line in remote_file:
#    print(line)
#finally:
#  remote_file.close()


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

def enumrate_file(remoteDir):
    # 实例化生成器, 获取sftp指定目录下的所有文件路径
    files = getRemoteFiles(remoteDir)
    i = 0
    # foreach遍历
    for file in files:
        i = i + 1
    print(i)

# 远程目录remoteDir文件下载保存到本地目录localDir
def download_file(remoteDir, outputDir):

    # 实例化生成器, 获取sftp指定目录下的所有文件路径
    files = getRemoteFiles(remoteDir)
    i = 0
    # foreach遍历
    for file in files:
        # 要下载的远程文件, 本地时路径+文件名
        #print(file)
        remoteFileName = file.split('/')[-2] + '/' + file.split('/')[-1]
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
            with open(outputDir + 'test.txt', 'w') as writer:
                for section in sections: #sections是一个list,section是一个{heading:xxx, text:yyy}的字典
                    for key in section.keys():
                        if section[key] == "Keywords" or section[key] == "Acknowledgements":
                            break
                        else:
                            writer.write(section['text'])
                            writer.write('\n')
                            break
            with open (outputDir + 'paragraph.txt', 'a') as writer:
                with open(outputDir + 'test.txt', 'r') as f:
                    writer.write('doi ' + remoteFileName + '\n')
                    line = f.readline()
                    next_line = f.readline()
                    while(next_line):
                        if len(next_line) < 35 or next_line[:3] == 'Fig' or next_line[:3] == 'www':
                            next_line = f.readline()
                        else:
                            if not next_line[0].isupper(): #如果开头是小写字母，代表上一段落还没结束
                                writer.write(line.strip() + ' ')
                                line = next_line
                            else:
                                writer.write(line)
                                line = next_line
                            next_line = f.readline()
                    writer.write(line)
            print(i)
        except Exception as e:
            print("there is no sections in" + file)

    sftp.close()

def tc_generation(outputDir):
    synthesis_tc = pd.DataFrame()
    doi = []
    now_doi = ''
    paragraph = [] 
    label = []
    i = 0
    for i in range(1784):
        label.append('')
    with open(outputDir + 'paragraph.txt', 'r') as f:
        line = f.readline()
        while (line):
            if line[:3] == 'doi':
                i = i+1
                now_doi = line.strip().split(' ')[1]
                line = f.readline()
            else:
                if line[:3] != 'www' and len(line) > 500:
                    doi.append(now_doi)
                    paragraph.append(line.strip())
                #if len(paragraph) == 2000:
                #    break
                line = f.readline()
    #print(i)
    print(len(doi))
    print(len(paragraph))
    synthesis_tc['doi'] = doi
    synthesis_tc['paragraph'] = paragraph
    synthesis_tc['synthesis_label'] = label
    synthesis_tc.to_csv(outputDir + 'synthesis_paragraph.csv', encoding='utf-8', index=False)

#enumrate_file('/mnt/ssd2/wld/gold_data/')
#download_file('/opt/mfs/duyi/cataly/photocataly_json/', 'synthesis_data/')
#tc_generation('synthesis_data/')
#download_file('/mnt/ssd2/wld/gold_data/', 'goldcorpus_data/')
#tc_generation('goldcorpus_data/')
download_file('/mnt/ssd2/wld/co2ANNOTATIAON/', 'labeled_data/')
tc_generation('labeled_data/')