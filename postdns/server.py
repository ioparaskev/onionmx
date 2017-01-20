import socket
import multiprocessing
import atexit


def close_socket(sock):
    sock.shutdown(socket.SHUT_RDWR)
    sock.close()


def rslv(rerouter, conn):
    try:
        postdns = rerouter()
        postdns.configure()
        while True:
            addr = conn.recv(1024).strip()
            if not addr:
                # connection ended
                return
            if addr == 'get *':
                conn.sendall("200 :\n")
            else:
                conn.sendall("{0}\n".format(postdns.run(addr)))
    except socket.timeout:
        return
    except BaseException as e:
        # todo log
        conn.sendall("500 :\n")


def daemonize_server(rerouter, port=2026):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 2026))
    sock.listen(1)
    atexit.register(close_socket, sock=sock)
    while True:
        conn, address = sock.accept()
        process = multiprocessing.Process(target=rslv, args=(rerouter,
                                                             conn))
        process.daemon = True
        process.start()
