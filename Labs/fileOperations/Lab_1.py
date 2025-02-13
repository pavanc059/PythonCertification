import os
from os import strerror


def readfile(filename:str) -> str:
    content = None
    try:
        filestrame = open(os.getcwd()+'\\Labs\\fileOperations\\'+filename, 'rt', encoding='utf-8')
        content = filestrame.read()
    except IOError as e:
        print("Cannot open file: ", strerror(e.errno))
        exit(e.errno)
    finally:
        filestrame.close()
    return content
    
def fileContentCounter(content:str) -> dict:
    content =  content.replace('\n', '')
    content =  content.replace(' ', '')
    content =  content.replace('\t', '')
    content =  content.replace('\r', '')
    content =  content.replace('\v', '')
    content =  content.lower()
    
    char_map = {}

    for char in content:
        if char in char_map:
            char_map[char] += 1
        else:
            char_map[char] = 1
    
    return char_map

def process():
    content = readfile('testdata.txt')
    char_map = fileContentCounter(content)

    char_map.items()

    # TODO: crate a sorted dictionary with values having highest count shown first
    for item, value in char_map.items():
        if value == 1:
            char_map.pop

    for char, count in char_map.items():
        print(f"{char} -> {count}")

process()