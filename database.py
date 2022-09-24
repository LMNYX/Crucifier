import struct
import re


class Buffer:
    def __init__(self, data):
        self.data = data
        self.offset = 0

    def _read(self, fmt, size):
        data = struct.unpack(fmt, self.data[self.offset:self.offset+size])[0]
        self.offset += size
        return data

    def _read_raw(self, size):
        data = self.data[self.offset:self.offset+size]
        self.offset += size
        return data

    def read_raw_bytes(self, size):
        return self._read_raw(size)

    def read_sbyte(self):
        return self._read("<b", 1)

    def read_ubyte(self):
        return self._read("<B", 1)

    def read_bool(self):
        return bool(self.read_ubyte())

    def read_char(self):
        return self._read("<c", 1)

    def read_short(self):
        return self._read("<h", 2)

    def read_ushort(self):
        return self._read("<H", 2)

    def read_int(self):
        return self._read("<i", 4)

    def read_uint(self):
        return self._read("<I", 4)

    def read_long(self):
        return self._read("<q", 8)

    def read_ulong(self):
        return self._read("<Q", 8)

    def read_float(self):
        return self._read("<f", 4)

    def read_double(self):
        return self._read("<d", 8)

    def read_byte_array(self):
        length = self.read_int()
        return self.read_raw_bytes(length) if length > 0 else None

    def _read_chars(self, length):
        return self.read_raw_bytes(length).decode('utf-8')

    def read_chars(self):
        length = self.read_int()
        return self._read_chars(length) if length > 0 else None

    def read_ulb128(self):
        result = 0
        shift = 0
        while True:
            byte = self.read_ubyte()
            result |= (byte & 0b01111111) << shift
            if (byte & 0b10000000) == 0x00:
                break
            shift += 7
        return result

    def read_string(self):
        if self.read_ubyte() != 0x0B:
            return
        length = self.read_ulb128()
        return self.read_raw_bytes(length).decode('utf-8')

    def read_datetime(self):
        return self._read("<q", 8)


class Cache:
    data = {}
    __slots__ = ()

    def __init__(self):
        for attr in self.__slots__:
            setattr(self, attr, None)

    @staticmethod
    def interpret_rtype(buf, rtype):
        m = re.match(r"(?P<rtype>.*)\[(?P<inrtype>.*)]", rtype)
        if m:
            return m.group("rtype"), m.group("inrtype")
        return getattr(buf, f"read_{rtype}")

    def read_buffer(self, buf, rtype):
        t = self.interpret_rtype(buf, rtype)
        if type(t) == str:
            return getattr(buf, f"read_{t.lower()}")
        t, it = t
        if t.lower() == "list":
            arr = []
            for _ in range(buf.read_uint()):
                arr.append(self.read_buffer(buf, it))
            return arr
        elif t.lower() == "cache":
            return globals()[it].from_data(buf)
        else:
            raise ValueError(f"Type {t} cannot contain a nested type.")

    @classmethod
    def from_path(cls, path):
        with open(path, "rb") as f:
            return cls.from_data(f.read())

    @classmethod
    def from_data(cls, data):
        if not isinstance(data, Buffer):
            data = Buffer(data)

        cache = cls()
        for attr, rtype in cls.data.keys():
            setattr(cache, attr, cache.read_buffer(data, rtype))

    def to_file(self, path):
        with open(path, "wb") as f:
            pass


class OsuCache(Cache):
    VERSION = 1
    data = {
        "version": "ushort",
        "beatmapsets": "list[cache[BeatmapsetCache]]"
    }
    __slots__ = tuple(data.values())


class BeatmapsetCache(Cache):
    data = {
        "": "",
    }
    __slots__ = tuple(data.values())
