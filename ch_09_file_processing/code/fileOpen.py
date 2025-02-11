import os


stream = open(os.getcwd()+'\\ch_09_file_processing\\code\\README.txt', 'rt', encoding='utf-8')
print(stream.read())