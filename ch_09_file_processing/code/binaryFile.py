from os import strerror



def writingBinaryFile():
    data = bytearray(10)
    for i in range(len(data)):
        data[i] = 10 + i

    try:
        bf = open('file.bin', 'wb')
        bf.write(data)
        bf.close()
    except IOError as e:
        print("I/O error occurred:", strerror(e.errno))


def readingBinaryFile():
    try:
        data = bytearray(10)
        bf = open('file.bin', 'rb')
        bf.readinto(data)
        bf.close()

        for b in data:
            print(hex(b), end=' ')


    except IOError as e:
        print("I/O error occurred:", strerror(e.errno))

writingBinaryFile()
readingBinaryFile()