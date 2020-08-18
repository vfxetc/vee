import struct
import re
import mmap
import sys

import elffile

DT_NULL = 0
DT_NEEDED = 1
DT_RPATH = 15
DT_RUNPATH = 29

class MyLib(object):
    
    def __init__(self, path):
        self._lib = elffile.open(path)
        self.headers = dict((h.name, h) for h in self._lib.sectionHeaders)
        self.load_dynstr()
        self.load_dynamic()

    def dump(self, fh):
        self.dump_dynamic()
        fh.write(self._lib.pack())

    def load_dynstr(self):

        self.dynstr = dynstr = self.headers['.dynstr']
        self.ptr_to_str = ptr_to_str = {}
        self.str_to_ptr = str_to_ptr = {}

        null = re.escape('\0')
        for m in re.finditer(r'[^%s]*%s' % (null, null), dynstr.content):
            ptr = m.start()
            value = m.group(0)[:-1]
            ptr_to_str[ptr] = value
            str_to_ptr[value] = ptr

    def add_string(self, x):
        ptr = len(self.dynstr.content)
        self.dynstr.content += x + '\0'
        return ptr

    def load_dynamic(self):

        self.dynamic = dynamic = self.headers['.dynamic']

        self.dyn_is_big = dynamic.coder.format.startswith('>')
        self.dyn_is_64b = 'Q' in dynamic.coder.format
        format = self.dyn_format = struct.Struct('<>'[self.dyn_is_big] + 2 * 'IQ'[self.dyn_is_64b])

        self.dyn_commands = []

        for i in range(0, dynamic.section_size, format.size):
            raw = dynamic.content[i:i+format.size]
            self.dyn_commands.append(list(format.unpack(raw)))

    def dump_dynamic(self):
        self.dynamic.content = ''.join(
            self.dyn_format.pack(*cmd) for cmd in self.dyn_commands
        )

    def add_needed(self, name):
        ptr = self.str_to_ptr.get(name)
        ptr = self.add_string(name) if ptr is None else ptr
        self.dyn_commands.insert(0, [DT_NEEDED, ptr])

    def _find_rpath(self):
        for cmd_to_find in (DT_RUNPATH, DT_RPATH):
            for i, cmd in enumerate(self.dyn_commands):
                if cmd[0] == cmd_to_find:
                    return cmd

    def get_rpath(self):
        cmd = self._find_rpath()
        if cmd:
            return self.ptr_to_str[cmd[1]]

    def set_rpath(self, path):
        new_ptr = self.add_string(path)
        cmd = self._find_rpath()
        if cmd:
            cmd[1] = new_ptr
        else:
            self.dyn_commands.insert(0, [DT_RUNPATH, new_ptr])














lib = MyLib(sys.argv[1])

for i, (tag, value) in enumerate(lib.dyn_commands):
    if tag == DT_NULL:
        print(i, 'DT_NULL')
    elif tag == DT_NEEDED:
        print(i, 'DT_NEEDED', lib.ptr_to_str[value])
    elif tag == DT_RUNPATH:
        print(i, 'DT_RUNPATH', lib.ptr_to_str[value])
    elif tag == DT_RPATH:
        print(i, 'DT_RPATH', lib.ptr_to_str[value])

lib.set_rpath('/path/to/libs')
lib.dump(open(sys.argv[1] + '-mod', 'wb'))




