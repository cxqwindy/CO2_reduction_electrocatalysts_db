import fitz
import re
import os
import glob

path = 'data/pdf_file'
def processing(old_paragraph, filename):
    with open('data/new_test.txt','a') as writer:
        if old_paragraph[0] != '[':
            paragraph = re.sub(r'(\d{1})\.(\d{1})',r'\1~\2',old_paragraph)
            paragraph = re.sub(r'\[[\d]+\]','',paragraph)
            samples=paragraph.split('.')
            for sample in samples:
                writer.write(filename + ' O '+'\n')
                words=sample.replace(',', ' ').replace('(', ' ').replace(')', ' ').replace('~', '.').split(' ')
                for word in words:
                    if word != '':
                        wordt = word.encode('utf-8', 'replace').decode()
                        writer.write(wordt+' O'+'\n')
                writer.write('\n')


if __name__=='__main__':
    files_path = glob.glob(os.path.join(path, "*.pdf"))
    output_file_path = 'data/test.txt'
    i=0
    with open('data/filename.txt','w') as writer:
        for f in files_path:
            writer.write(f.replace('.pdf','').replace('data/pdf_file/','')+'\n')
    for f in files_path:
        i=i+1
        #print(f)
        doc = fitz.open(f)
        #print(doc.page_count)
        #print(doc.metadata)
        with open(output_file_path, 'a') as t_out:
            for page in doc:
                text_list = page.get_text('blocks')
                for text in text_list:
                    #processing(text[4].replace('\n', ''), f.replace('.pdf','').replace('data/pdf_file/',''))
                    line = text[4].encode('utf-8', 'replace').decode()
                    #t_out.write(line.replace('\n','')+'\n')
    doc = fitz.open('data/pdf_file/10.1002_adfm.202101255.pdf')
    #output_file_path = 'data/test.txt'
    #print(doc.page_count)
    #print(doc.metadata)
    #texts = ""
    for page in doc:
        #texts += page.get_text()
        #print(page.get_text('html'))
    #print(texts)
    #text_list = texts.split('\n')
    #with open(output_file_path, 'w', encoding = 'utf-8') as f_out:
        #for page in doc:
            #text_list = page.get_text('blocks')
            #for text in text_list:
                #processing(text[4].replace('\n', ''))
                #f_out.write(text[4].replace('\n', ''))
                #f_out.write('\n')
        #for text in text_list:
            #f_out.write(text)
            #f_out.write('\nbalabala')
