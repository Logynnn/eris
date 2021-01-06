import typing
import inspect
import json
from collections import OrderedDict

import asyncpg


class SchemaError(Exception):
    pass

class SQLType:
    python: typing.Any = None

    def to_sql(self) -> str:
        raise NotImplementedError()

class String(SQLType):
    python = str

    def to_sql(self):
        return 'TEXT'

class Column:
    __slots__ = (
        'column_type', 'index', 'primary_key', 'nullable',
        'default', 'unique', 'name', 'index_name'
    )

    def __init__(self, column_type: SQLType, *, index: bool=False, primary_key: bool=False,
                 nullable: bool=False, unique: bool=False, default: typing.Any=None, name: str=None):
        
        if inspect.isclass(column_type):
            column_type = column_type()

        if not isinstance(column_type, SQLType):
            raise TypeError('Cannot have a non-SQLType derived column_type')

        self.column_type = column_type
        self.index = index
        self.primary_key = primary_key
        self.nullable = nullable
        self.unique = unique
        self.default = default
        self.name = name
        self.index_name = None

        if sum(map(bool, (unique, primary_key, default is not None))) > 1:
            raise SchemaError('\'unique\', \'primary_key\' and \'default\' are mutually exclusive')

    def _create_table(self) -> str:
        builder = []
        builder.append(self.name)
        builder.append(self.column_type.to_sql())

        default = self.default
        if default is not None:
            builder.append('DEFAULT')

            if isinstance(default, str) and isinstance(self.column_type, String):
                builder.append('\'%s\'' % default)
            elif isinstance(default, bool):
                builder.append(str(default).upper())
            else:
                builder.append('(%s)' % default)
        elif self.unique:
            builder.append('UNIQUE')
        
        if not self.nullable:
            builder.append('NOT NULL')

        return ' '.join(builder)

class TableMeta(type):
    @classmethod
    def __prepare__(cls, *args, **kwargs):
        return OrderedDict()

    def __new__(cls, name, parents, dct, **kwargs):
        columns = []
        table_name = kwargs.get('table_name', name.lower())

        dct['__table_name__'] = table_name

        for elem, value in dct.items():
            if isinstance(value, Column):
                if value.name is None:
                    value.name = elem

                if value.index:
                    value.index_name = '%s_%s_idx' % (table_name, value.name)

                columns.append(value)

        dct['columns'] = columns
        return super().__new__(cls, name, parents, dct)

    def __init__(self, name, parents, dct, **kwargs):
        super().__init__(name, parents, dct)

class Table(metaclass=TableMeta):
    @classmethod
    async def create_pool(cls, uri: str, **kwargs):
        '''Configura e retorna uma pool do PostgreSQL.'''
        def _encode_jsonb(value):
            return json.dumps(value)

        def _decode_jsonb(value):
            return json.loads(value)

        async def init(conn: asyncpg.Connection):
            await conn.set_type_codec('jsonb', schema='pg_catalog', encoder=_encode_jsonb, decoder=_decode_jsonb)

        return await asyncpg.create_pool(uri, init=init, **kwargs)

    @classmethod
    async def create(cls, pool: asyncpg.pool.Pool, *, verbose: bool=False) -> typing.Optional[bool]:
        '''Cria o banco de dados.'''
        sql = cls.create_table(exists_ok=True)
        if verbose:
            print(sql)

        await pool.execute(sql)

    @classmethod
    def create_table(cls, *, exists_ok: bool=True) -> str:
        '''Gera uma query CREATE TABLE.'''
        statements = []
        builder = ['CREATE TABLE']

        if exists_ok:
            builder.append('IF NOT EXISTS')

        builder.append(cls.__table_name__)

        column_creations = []
        primary_keys = []

        for column in cls.columns:
            column_creations.append(column._create_table())

            if column.primary_key:
                primary_keys.append(column.name)

        if primary_keys:
            column_creations.append('PRIMARY KEY (%s)' % ', '.join(primary_keys))
            
        builder.append('(%s)' % ', '.join(column_creations))
        statements.append(' '.join(builder))

        for column in cls.columns:
            if column.index:
                fmt = 'CREATE INDEX IF NOT EXISTS {1.index_name} ON {0} ({1.name});'.format(cls.__table_name__, column)
                statements.append(fmt)

        return '\n'.join(statements)

    @classmethod
    def all_tables(cls):
        return cls.__subclasses__()