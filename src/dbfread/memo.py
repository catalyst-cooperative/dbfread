"""
Reads data from FPT (memo) files.

FPT files are used to varying lenght text or binary data which is too
large to fit in a DBF field.

VFP == Visual FoxPro
DB3 == dBase III
DB4 == dBase IV
"""
import io

from dbfread.ifiles import ifind
from dbfread.struct_parser import StructParser

VFPFileHeader = StructParser(
    'FPTHeader',
    '>LHH504s',
    ['nextblock',
     'reserved1',
     'blocksize',
     'reserved2'])

VFPMemoHeader = StructParser(
    'FoxProMemoHeader',
    '>LL',
    ['type',
     'length'])

DB4MemoHeader = StructParser(
    'DBase4MemoHeader',
    '<LL',
    ['reserved',  # Always 0xff 0xff 0x08 0x08.
     'length'])



class VFPMemo(bytes):
    pass


# Used for Visual FoxPro memos to distinguish binary from text memos.
class BinaryMemo(VFPMemo):
    pass


class PictureMemo(BinaryMemo):
    pass


class ObjectMemo(BinaryMemo):
    pass


class TextMemo(VFPMemo):
    pass


VFP_TYPE_MAP = {
    0x0: PictureMemo,
    0x1: TextMemo,
    0x2: ObjectMemo,
}


class FakeMemoFile(io.BytesIO):
    def __getitem__(self, i):
        return None


class VFPMemoFile(io.BytesIO):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header = VFPFileHeader.read(self)

    def __getitem__(self, index):
        """Get a memo from the file."""
        if index <= 0:
            return None

        self.seek(index * self.header.blocksize)
        memo_header = VFPMemoHeader.read(self)

        data = self.read(memo_header.length)

        if len(data) != memo_header.length:
            raise IOError('EOF reached while reading memo')

        return VFP_TYPE_MAP.get(memo_header.type, BinaryMemo)(data)


class DB3MemoFile(io.BytesIO):
    """dBase III memo file."""

    def __getitem__(self, index):
        if index <= 0:
            return None

        block_size = 512
        self.seek(index * block_size)
        data = b''

        while True:
            newdata = self.read(block_size)

            if not newdata:
                return data

            data += newdata

            # Todo: some files (help.dbt) has only one field separator.
            # Is this enough for all file though?
            end_of_memo = data.find(b'\x1a')

            if end_of_memo != -1:
                return data[:end_of_memo]

            # Alternative end of memo markers:
            # \x1a\x1a
            # \x0d\x0a


class DB4MemoFile(io.BytesIO):
    """dBase IV memo file"""

    def __getitem__(self, index):
        if index <= 0:
            return None

        # Todo: read this from the file header.
        block_size = 512

        self.seek(index * block_size)
        memo_header = DB4MemoHeader.read(self)
        data = self.read(memo_header.length)
        # Todo: fields are terminated in different ways.
        # \x1a is one of them
        # \x1f seems to be another (dbase_8b.dbt)
        return data.split(b'\x1f', 1)[0]


def find_memofile(dbf_filename):
    for ext in ['.fpt', '.dbt']:
        name = ifind(dbf_filename, ext=ext)
        if name:
            return name
    else:
        return None


def open_memofile(filename, dbversion):

    with open(filename, 'rb') as data:
        if filename.lower().endswith('.fpt'):
            return VFPMemoFile(data.read())
        else:
            # print('######', dbversion)
            if dbversion == 0x83:
                return DB3MemoFile(data.read())
            else:
                return DB4MemoFile(data.read())
