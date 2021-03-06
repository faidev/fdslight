#!/usr/bin/env python3
import pywind.lib.reader as reader


class ProtocolErr(Exception): pass


class MsgSocketWantReadErr(Exception): pass


class wrap_socket(object):
    """进程间通讯协议
    sync_code:8 bytes,每个字节固定为 0x00
    payload_length:2 bytes 内容长度
    payload_content
    """
    # 一个帧是否结束
    __frame_finish = True
    __reader = None
    __sync_code = None

    __payload_length = 0
    __read_length = 0

    __received_data = None
    __socket = None

    def __init__(self, s):
        self.__frame_finish = True
        self.__reader = reader.reader()
        self.__sync_code = bytes(8)
        self.__reset()
        self.__socket = s

    def __wrap_sent_data(self, byte_data):
        size = len(byte_data)
        sent_data = b"".join([
            self.__sync_code,
            bytes(((size & 0xff00) >> 8, size & 0x00ff,)),
            byte_data,
        ])

        return sent_data

    def __parse_recv_data(self):
        if self.__frame_finish:
            if self.__reader.size() < 10: return (False, b"",)
            sync_code = self.__reader.read(8)
            if sync_code != self.__sync_code: raise ProtocolErr("wrong sync code")
            tmp_data = self.__reader.read(2)
            self.__payload_length = (tmp_data[0] << 8) | tmp_data[1]

        if self.__payload_length < self.__reader.size():
            read_length = self.__payload_length
        else:
            read_length = self.__reader.size()

        read_data = self.__reader.read(read_length)
        self.__read_length += read_length
        read_ok = self.__payload_length == self.__read_length
        self.__frame_finish = read_ok

        return (read_ok, read_data,)

    def __recv_data(self, callback, *args, **kwargs):
        if self.__frame_finish and self.__reader.size() >= 10:
            read_ok, byte_data = self.__parse_recv_data()
            self.__received_data.append(byte_data)
            if not read_ok:
                recv_data = callback(*args, **kwargs)
                self.__reader._putvalue(recv_data)
                raise MsgSocketWantReadErr

            result_data = b"".join(self.__received_data)
            self.__reset()

            return result_data

        recv_data = callback(*args, **kwargs)
        self.__reader._putvalue(recv_data)
        read_ok, byte_data = self.__parse_recv_data()
        self.__received_data.append(byte_data)

        if read_ok:
            result_data = b"".join(self.__received_data)
            self.__reset()
            return result_data
        raise MsgSocketWantReadErr

    def recv(self, bufsize, *args, **kwargs):
        bufsize += 10
        args = list(args)

        if args:
            args.insert(0, bufsize)
        else:
            args.append(bufsize)

        args = tuple(args)

        return self.__recv_data(self.__socket.recv, *args, **kwargs)

    def send(self, byte_data, *args, **kwargs):
        sent_data = self.__wrap_sent_data(byte_data)

        return self.__socket.send(sent_data, *args, **kwargs)

    def sendall(self, data, flags=None):
        sent_data = self.__wrap_sent_data(data)

        return self.__socket.sendall(sent_data, flags=flags)

    def __reset(self):
        self.__payload_length = 0
        self.__read_length = 0
        self.__frame_finish = True
        self.__received_data = []

    def bind(self, address):
        return self.__socket.bind(address)

    def accept(self):
        return self.__socket.accept()

    def listen(self, backlog):
        return self.__socket.listen(backlog)

    def connect(self, address):
        return self.__socket.connect(address)

    def connect_ex(self, address):
        return self.__socket.connect_ex(address)

    def setblocking(self, flag):
        return self.__socket.setblocking(flag)

    def setsockopt(self, level, option, value):
        return self.__socket.setsockopt(level, option, value)

    def settimeout(self, timeout):
        return self.__socket.settimeout(timeout)
