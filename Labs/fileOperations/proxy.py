import socket
import threading

def pipe(source, destination):
    try:
        while True:
            data = source.recv(4096)
            if not data:
                break
            destination.sendall(data)
    except:
        pass
    finally:
        source.close()
        destination.close()

def start_proxy():
    # Listen on ALL interfaces on port 27019
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', 27019))
    server.listen(5)
    print("Proxy active: Listening on 0.0.0.0:27019 --> Forwarding to 127.0.0.1:27018")

    while True:
        client_sock, addr = server.accept()
        print(f"Connection received from {addr}")
        
        # Connect to your local MongoDB
        target_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        target_sock.connect(('127.0.0.1', 27018))
        
        # Start two threads to pass data back and forth
        threading.Thread(target=pipe, args=(client_sock, target_sock), daemon=True).start()
        threading.Thread(target=pipe, args=(target_sock, client_sock), daemon=True).start()

if __name__ == "__main__":
    start_proxy()
