'''
MIT License

Copyright (c) 2021 Caio Alexandre

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
'''
'''
This Source Code Form is subject to the
terms of the Mozilla Public License, v.
2.0. If a copy of the MPL was not
distributed with this file, You can
obtain one at
http://mozilla.org/MPL/2.0/.
'''

import json
import typing
from asyncio import AbstractEventLoop
from collections import OrderedDict

import asyncpg
import colorama


DIM   = colorama.Style.DIM
RESET = colorama.Style.RESET_ALL


async def create_pool(dsn: str, *, loop: AbstractEventLoop) -> asyncpg.Pool:
    '''Criar um pool de conexão no PostgreSQL.

    Parameters
    ----------
    dsn: :class:`str`
        Argumentos de conexão especificadas em uma única string.
    loop: :class:`AbstractEventLoop`
        O loop assíncrono de eventos.
    
    Returns
    -------
    :class:`asyncpg.Pool`
        Uma instância do pool de conexão do PostgreSQL.
    '''

    # As seguintes fazem que, quando o banco de dados
    # retornar algum JSON, converta para um dicionário.
    # Caso contrário uma `str` é retornada.
    def _encode_jsonb(value):
        return json.dumps(value)

    def _decode_jsonb(value):
        return json.loads(value)

    async def init(conn: asyncpg.Connection):
        await conn.set_type_codec('jsonb', schema='pg_catalog', encoder=_encode_jsonb, decoder=_decode_jsonb)

    return await asyncpg.create_pool(dsn, loop=loop, init=init)


class SchemaError(Exception):
    pass


class SQLType:
    def to_sql(self) -> str:
        raise NotImplementedError()


class Boolean(SQLType):
    def to_sql(self):
        return 'BOOLEAN'


class Datetime(SQLType):
    def __init__(self, *, timezone=False):
        self.timezone = timezone

    def to_sql(self):
        if self.timezone:
            return 'TIMESTAMP WITH TIME ZONE'
        return 'TIMESTAMP'


class Integer(SQLType):
    def __init__(self, *, big=False, small=False, auto_increment=False):
        self.big = big
        self.small = small
        self.auto_increment = auto_increment

        if big and small:
            raise SchemaError('Integer column type cannot be both big and small')

    def to_sql(self):
        if self.auto_increment:
            if self.big:
                return 'BIGSERIAL'
            if self.small:
                return 'SMALLSERIAL'
            return 'SERIAL'

        if self.big:
            return 'BIGINT'
        if self.small:
            return 'SMALLINT'
        return 'INTEGER'


class String(SQLType):
    def __init__(self, *, length=None, fixed=False):
        if fixed and length is None:
            raise SchemaError('Cannot have a fixed string with no length')

        self.length = length
        self.fixed = fixed

    def to_sql(self):
        if self.length is None:
            return 'TEXT'

        if self.fixed:
            return f'CHAR({self.length})'
        return f'VARCHAR({self.length})'


class Json(SQLType):
    def to_sql(self):
        return 'JSONB'


class ForeignKey(SQLType):
    def __init__(self, table, column, *, sql_type=None, on_delete='CASCADE', on_update='NO ACTION'):
        if not table or not isinstance(table, str):
            raise SchemaError('Missing table to reference (must be string)')

        valid_actions = (
            'NO ACTION',
            'RESTRICT',
            'CASCADE',
            'SET NULL',
            'SET DEFAULT'
        )

        on_delete = on_delete.upper()
        on_update = on_update.upper()

        if on_delete not in valid_actions:
            raise TypeError('on_delete must be one of %s.' % valid_actions)

        if on_update not in valid_actions:
            raise TypeError('on_update must be one of %s.' % valid_actions)

        self.table = table
        self.column = column
        self.on_update = on_update
        self.on_delete = on_delete

        if not sql_type:
            sql_type = Integer

        if isinstance(sql_type, type):
            sql_type = sql_type()

        if not isinstance(sql_type, SQLType):
            raise TypeError('Column type must be an instance of SQLType')

        self.sql_type = sql_type.to_sql()

    def to_sql(self):
        fmt = '{0.sql_type} REFERENCES {0.table} ({0.column}) ' \
              'ON DELETE {0.on_delete} ON UPDATE {0.on_update}'
        return fmt.format(self)


class Column:
    def __init__(self, column_type, *, index=False, primary_key=False, nullable=False, unique=False, default=None, name=None):
        if isinstance(column_type, type):
            column_type = column_type()

        if not isinstance(column_type, SQLType):
            raise TypeError('Column type must be an instance of SQLType')

        if sum(map(bool, (unique, primary_key, default is not None))) > 1:
            raise SchemaError("'unique', 'primary_key' and 'default' are mutually exclusive")

        self.column_type = column_type
        self.index = index
        self.primary_key = primary_key
        self.nullable = nullable
        self.unique = unique
        self.default = default
        self.name = name

        # Para ser preenchido depois.
        self.index_name = None

    def to_sql(self) -> str:
        builder = []

        builder.append(self.name)
        builder.append(self.column_type.to_sql())

        default = self.default
        if default is not None:
            builder.append('DEFAULT')

            if isinstance(default, str) and isinstance(self.column_type, String):
                builder.append("'%s'" % default)
            elif isinstance(default, bool):
                builder.append(str(default).upper())
            else:
                builder.append('(%s)' % default)
        elif self.unique:
            builder.append('UNIQUE')

        if not self.nullable:
            builder.append('NOT NULL')

        return ' '.join(builder)


class PrimaryKeyColumn(Column):
    '''Atalho para uma coluna SERIAL PRIMARY KEY.'''

    def __init__(self):
        super().__init__(Integer(auto_increment=True), primary_key=True)


class TableMeta(type):
    @classmethod
    def __prepare__(cls, *args, **kwargs):
        return OrderedDict()

    def __new__(cls, name, parents, dct, **kwargs):
        columns = []
        table_name = kwargs.get('table_name', name.lower())

        dct['__table_name__'] = table_name

        for elem, value in dct.items():
            if not isinstance(value, Column):
                continue

            if not value.name:
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
    async def create(cls, pool: asyncpg.Pool, *, verbose: bool = False):
        '''Cria uma tabela no banco de dados.

        Parameters
        ----------
        pool: :class:`asyncpg.Pool`
            O pool de conexão do PostgreSQL.
        verbose: Optional[:class:`bool`]
            Se a criação da tabela deve ser "barulhenta". Por padrão é `False`.
        '''
        sql = cls.create_table(exists_ok=True)

        if verbose:
            print(DIM + sql + RESET)

        await pool.execute(sql)

    @classmethod
    def create_table(cls, *, exists_ok: bool = True) -> str:
        '''Gera uma query SQL do tipo `CREATE TABLE`.

        Parameters
        ----------
        exists_ok: Optional[:class:`str`]
            Se deve ignorar caso a tabela já exista. Por padrão é `True`.

        Returns
        -------
        :class:`str`
            A query SQL formatada.
        '''
        statements = []
        builder = ['CREATE TABLE']

        if exists_ok:
            builder.append('IF NOT EXISTS')

        builder.append(cls.__table_name__)

        column_creations = []
        primary_keys = []

        for column in cls.columns:
            column_creations.append(column.to_sql())

            if column.primary_key:
                primary_keys.append(column.name)

        if primary_keys:
            column_creations.append('PRIMARY KEY (%s)' % ', '.join(primary_keys))

        builder.append('(%s)' % ', '.join(column_creations))
        statements.append(' '.join(builder) + ';')

        for column in cls.columns:
            if column.index:
                fmt = 'CREATE INDEX IF NOT EXISTS {1.index_name} ON {0} ({1.name});'
                statements.append(fmt.format(cls.__table_name__, column))

        return '\n'.join(statements)

    @classmethod
    def all_tables(cls):
        return cls.__subclasses__()
