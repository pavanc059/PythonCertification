from os import strerror
import os

def readcharactest():
    try:
        counter = 0
        filestream = open(os.getcwd()+'\\ch_09_file_processing\\code\\README.txt', 'rt', encoding='utf-8')
        character = filestream.read(1)
        while character != '':
            print(character, end='')
            counter += 1
            character = filestream.read(1)
        filestream.close()
        print("\n\nCharacters in file:", counter)
    except IOError as e:
        print("I/O error occurred: ", strerror(e.errno))
        exit(e.errno)

def readFullFileintoMemory():
    try:
        cnt = 0
        s = open(os.getcwd()+'\\ch_09_file_processing\\code\\README.txt', "rt")
        content = s.read()
        for ch in content:
            print(ch, end='')
            cnt += 1
        s.close()
        print("\n\nCharacters in file:", cnt)
    except IOError as e:
        print("I/O error occurred: ", strerror(e.errno))

def readLinebyline():
    try:
        ccnt = lcnt = 0
        s = open(os.getcwd()+'\\ch_09_file_processing\\code\\README.txt', "rt")
        line = s.readline()
        while line != '':
            lcnt += 1
            for ch in line:
                print(ch, end='')
                ccnt += 1
            line = s.readline()
        s.close()
        print("\n\nCharacters in file:", ccnt)
        print("Lines in file:     ", lcnt)
    except IOError as e:
        print("I/O error occurred:", strerror(e.errno)) 

def readlines():
    try:
        ccnt = lcnt = 0
        s = open(os.getcwd()+'\\ch_09_file_processing\\code\\README.txt', "rt")
        lines = s.readlines(5)
        print(lines)
        while len(lines) != 0:
            for line in lines:
                lcnt += 1
                for ch in line:
                    print(ch, end='')
                    ccnt += 1
            lines = s.readlines(10)
        s.close()
        print("\n\nCharacters in file:", ccnt)
        print("Lines in file:     ", lcnt)
    except IOError as e:
        print("I/O error occurred:", strerror(e.errno))


def readtextfileUsingIterator():
    try:
        ccnt = lcnt = 0
        for line in open(os.getcwd()+'\\ch_09_file_processing\\code\\README.txt', "rt"):
            lcnt += 1
            for ch in line:
                print(ch, end='')
                ccnt += 1
        print("\n\nCharacters in file:", ccnt)
        print("Lines in file:     ", lcnt)
    except IOError as e:
        print("I/O error occurred: ", strerror(e.errno))

readtextfileUsingIterator()