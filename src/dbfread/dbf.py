"""Class to read DBF files."""
from copy import deepcopy
import os
import datetime
import platform
import collections
import io
import sys

from dbfread.ifiles import ifind
from dbfread.struct_parser import StructParser
from dbfread.field_parser import FieldParser
from dbfread.memo import find_memofile, open_memofile, FakeMemoFile
from dbfread.codepages import guess_encoding
from dbfread.dbversions import get_dbversion_string
from dbfread.exceptions import DBFNotFound, MissingMemoFile

_py_version = (sys.version_info.major, sys.version_info.minor)
_py_impl = platform.python_implementation()
if _py_version >= (3, 7) or (_py_version == (3, 6) and _py_impl == 'CPython'):
    ORDERED_DICT = dict
else:
    ORDERED_DICT = collections.OrderedDict

DBFHeader = StructParser(
    'DBFHeader',
    '<BBBBLHHHBBLLLBBH',
    ['dbversion',
     'year',
     'month',
     'day',
     'numrecords',
     'headerlen',
     'recordlen',
     'reserved1',
     'incomplete_transaction',
     'encryption_flag',
     'free_record_thread',
     'reserved2',
     'reserved3',
     'mdx_flag',
     'language_driver',
     'reserved4',
     ])

DBFField = StructParser(
    'DBFField',
    '<11scLBBHBBBB7sB',
    ['name',
     'type',
     'address',
     'length',
     'decimal_count',
     'reserved1',
     'workarea_id',
     'reserved2',
     'reserved3',
     'set_fields_flag',
     'reserved4',
     'index_field_flag',
     ])


def expand_year(year):
    """Convert 2-digit year to 4-digit year."""
    if year < 80:
        return 2000 + year
    else:
        return 1900 + year


class RecordIterator(object):
    def __init__(self, table, record_type):
        self._record_type = record_type
        self._table = table

    def __iter__(self):
        return self._table._iter_records(self._record_type)

    def __len__(self):
        return self._table._count_records(self._record_type)


class DBF(object):
    """DBF table."""

    def __init__(self, filename, encoding=None, ignorecase=True,
                 lowernames=False,
                 parserclass=FieldParser,
                 recfactory=ORDERED_DICT,
                 load=False,
                 raw=False,
                 ignore_missing_memofile=False,
                 char_decode_errors='strict',
                 filedata=None,
                 memofile=None):

        self.encoding = encoding
        self.ignorecase = ignorecase
        self.lowernames = lowernames
        self.parserclass = parserclass
        self.raw = raw
        self.ignore_missing_memofile = ignore_missing_memofile
        self.char_decode_errors = char_decode_errors

        if recfactory is None:
            self.recfactory = lambda items: items
        else:
            self.recfactory = recfactory

        # Name part before .dbf is the table name
        self.name = os.path.basename(filename)
        self.name = os.path.splitext(self.name)[0].lower()
        self._records = None
        self._deleted = None

        if filedata is not None:
            self._dbf_bytes = io.BytesIO(filedata.read())
            self.filename = filename
        elif ignorecase:
            self.filename = ifind(filename)
            if not self.filename:
                raise DBFNotFound(f'could not find file {filename!r}')
        else:
            self.filename = filename

        # Filled in by self._read_headers()
        self.header = None
        self.fields = []       # namedtuples
        self.field_names = []  # strings

        with self.dbf_bytes() as infile:
            self._read_header(infile)
            self._read_field_headers(infile)
            self._check_headers()

            try:
                self.date = datetime.date(expand_year(self.header.year),
                                          self.header.month,
                                          self.header.day)
            except ValueError:
                # Invalid date or '\x00\x00\x00'.
                self.date = None

        if memofile is None:
            self.memofilename = self._get_memofilename()
        else:
            self._memofile = memofile

        if load:
            self.load()

    @property
    def dbversion(self):
        return get_dbversion_string(self.header.dbversion)

    def dbf_bytes(self):
        """Produce a fresh copy of the DBF bytes as a file-like object."""
        if getattr(self, "_dbf_bytes", None) is not None:
            self._dbf_bytes.seek(0)
            return io.BytesIO(self._dbf_bytes.read())

        return open(self.filename, "rb")

    def _get_memofilename(self):
        # Does the table have a memo field?
        field_types = [field.type for field in self.fields]
        if not set(field_types) & set('MGPB'):
            # No memo fields.
            return None

        path = find_memofile(self.filename)
        if path is None:
            if self.ignore_missing_memofile:
                return None
            else:
                raise MissingMemoFile(f'missing memo file for {self.filename}')
        else:
            return path

    @property
    def loaded(self):
        """Return ``True`` if records are loaded into memory."""
        return self._records is not None

    def load(self):
        """Load records into memory.

        This loads both records and deleted records. The ``records``
        and ``deleted`` attributes will now be lists of records.

        """
        if not self.loaded:
            self._records = list(self._iter_records(b' '))
            self._deleted = list(self._iter_records(b'*'))

    def unload(self):
        """Unload records from memory.

        The records and deleted attributes will now be instances of
        ``RecordIterator``, which streams records from disk.
        """
        self._records = None
        self._deleted = None

    @property
    def records(self):
        """Records (not included deleted ones). When loaded a list of records,
        when not loaded a new ``RecordIterator`` object.
        """
        if self.loaded:
            return self._records
        else:
            return RecordIterator(self, b' ')

    @property
    def deleted(self):
        """Deleted records. When loaded a list of records, when not loaded a
        new ``RecordIterator`` object.
        """
        if self.loaded:
            return self._deleted
        else:
            return RecordIterator(self, b'*')

    def _read_header(self, infile):
        # Todo: more checks?
        self.header = DBFHeader.read(infile)

        if self.encoding is None:
            try:
                self.encoding = guess_encoding(self.header.language_driver)
            except LookupError:
                self.encoding = 'ascii'

    def _decode_text(self, data):
        return data.decode(self.encoding, errors=self.char_decode_errors)

    def _read_field_headers(self, infile):
        while True:
            sep = infile.read(1)
            if sep in (b'\r', b'\n', b''):
                # End of field headers
                break

            field = DBFField.unpack(sep + infile.read(DBFField.size - 1))

            field.type = chr(ord(field.type))

            # For character fields > 255 bytes the high byte
            # is stored in decimal_count.
            if field.type in 'C':
                field.length |= field.decimal_count << 8
                field.decimal_count = 0

            # Field name is b'\0' terminated.
            field.name = self._decode_text(field.name.split(b'\0')[0])
            if self.lowernames:
                field.name = field.name.lower()

            self.field_names.append(field.name)

            self.fields.append(field)

    def _open_memofile(self):
        if getattr(self, "_memofile", None) is not None:
            self._memofile.seek(0)
            return deepcopy(self._memofile)

        if self.memofilename and not self.raw:
            return open_memofile(self.memofilename, self.header.dbversion)
        else:
            return FakeMemoFile(self.memofilename)

    def _check_headers(self):
        """Check headers for possible format errors."""
        field_parser = self.parserclass(self)

        for field in self.fields:

            if field.type == 'I' and field.length != 4:
                message = 'Field type I must have length 4 (was {})'
                raise ValueError(message.format(field.length))

            elif field.type == 'L' and field.length != 1:
                message = 'Field type L must have length 1 (was {})'
                raise ValueError(message.format(field.length))

            elif not field_parser.field_type_supported(field.type):
                # Todo: return as byte string?
                raise ValueError(f'Unknown field type: {field.type!r}')

    def _skip_record(self, infile):
        # -1 for the record separator which was already read.
        infile.seek(self.header.recordlen - 1, 1)

    def _count_records(self, record_type=b' '):
        count = 0

        with self.dbf_bytes() as infile:
            # Skip to first record.
            infile.seek(self.header.headerlen, 0)

            while True:
                sep = infile.read(1)
                if sep == record_type:
                    count += 1
                    self._skip_record(infile)
                elif sep in (b'\x1a', b''):
                    # End of records.
                    break
                else:
                    self._skip_record(infile)

        return count

    def _iter_records(self, record_type=b' '):
        with self.dbf_bytes() as infile, \
                self._open_memofile() as memofile:

            # Skip to first record.
            infile.seek(self.header.headerlen, 0)

            if self.raw:
                def parse(_, data):
                    return data
            else:
                field_parser = self.parserclass(self, memofile)
                parse = field_parser.parse

            # Shortcuts for speed.
            skip_record = self._skip_record
            read = infile.read

            while True:
                sep = read(1)

                if sep == record_type:
                    if self.raw:
                        items = [(field.name, read(field.length))
                                 for field in self.fields]
                    else:
                        items = [(field.name,
                                  parse(field, read(field.length)))
                                 for field in self.fields]

                    yield self.recfactory(items)

                elif sep in (b'\x1a', b''):
                    # End of records.
                    break
                else:
                    skip_record(infile)

    def __iter__(self):
        if self.loaded:
            return list.__iter__(self._records)
        else:
            return self._iter_records()

    def __len__(self):
        return len(self.records)

    def __repr__(self):
        if self.loaded:
            status = 'loaded'
        else:
            status = 'unloaded'
        return f'<{status} DBF table {self.filename!r}>'

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.unload()
        return False
