import socket
import multiprocessing
import atexit


def close_socket(sock):
    sock.shutdown(socket.SHUT_RDWR)
    sock.close()


def rslv(rerouter, conn):
    try:
        while True:
            addr = conn.recv(1024).strip()
            if not addr:
                # connection ended
                return
            if addr == 'get *':
                conn.sendall("200 :\n")
            else:
                conn.sendall("{0}\n".format(rerouter.run(addr)))
    except socket.timeout:
        return
    except BaseException as err:
        # todo log
        conn.sendall("500 {0}".format(err))


def daemonize_server(rerouter, host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))
    sock.listen(1)
    atexit.register(close_socket, sock=sock)
    while True:
        conn, address = sock.accept()
        process = multiprocessing.Process(target=rslv, args=(rerouter,
                                                             conn))
        process.daemon = True
        process.start()
