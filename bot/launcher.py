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

import colorama
import asyncio
import importlib
import traceback
import logging
import contextlib
from logging.handlers import RotatingFileHandler
from pathlib import Path

import click
import humanize

import config
from eris import Eris
from utils.database import create_pool, Table
from utils.modules import get_all_extensions


colorama.init()


GREEN = colorama.Fore.LIGHTGREEN_EX
RED   = colorama.Fore.LIGHTRED_EX
DIM   = colorama.Style.DIM
RESET = colorama.Style.RESET_ALL


class RemoveNoise(logging.Filter):
    def __init__(self):
        super().__init__(name='discord.state')

    def filter(self, record: logging.LogRecord):
        if record.levelname == 'WARNING' and 'referencing an unknown' in record.msg:
            return False
        return True


@contextlib.contextmanager
def setup_logging():
    # Criar a pasta `logs/` antes de inicializar o logger.
    path = Path('logs')
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)

    try:
        # __enter__
        max_bytes = 32 * 1024 * 1024 # 32 MiB

        logging.getLogger('discord').setLevel(logging.INFO)
        logging.getLogger('discord.http').setLevel(logging.WARN)
        logging.getLogger('discord.state').addFilter(RemoveNoise())

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        dt_format = r'%Y-%m-%d %H:%M:%S'
        log_format = '[{asctime}] [{levelname}] {name}: {message}'

        kwargs = {'filename': 'logs/eris.log', 'encoding': 'utf-8', 'mode': 'w'}
        handler = RotatingFileHandler(**kwargs, maxBytes=max_bytes, backupCount=5)
        formatter = logging.Formatter(log_format, dt_format, style='{')

        handler.setFormatter(formatter)
        logger.addHandler(handler)

        yield
    finally:
        # __exit__
        for handler in logger.handlers:
            handler.close()
            logger.removeHandler(handler)


def run_bot():
    # Ativamos o i18n em português do módulo `humanize`.
    humanize.activate('pt_BR')

    bot = Eris()
    bot.run(config.token)


@click.group(invoke_without_command=True, options_metavar='[options]')
@click.pass_context
def main(ctx: click.Context):
    '''Inicializa o bot.'''
    if not ctx.invoked_subcommand:
        with setup_logging():
            run_bot()


@main.group(short_help='coisas do banco de dados', options_metavar='[options]')
def db():
    pass


@db.command(short_help='inicializa o banco de dados', options_metavar='[options]')
@click.option('-q', '--quiet', help='output menos detalhado', is_flag=True)
def init(quiet: bool):
    '''Faz a criação das tabelas do PostgreSQL automaticamente.'''
    loop = asyncio.get_event_loop()
    run = loop.run_until_complete

    pool = run(create_pool(config.postgres, loop=loop))

    for ext in get_all_extensions():
        try:
            importlib.import_module(ext)
        except Exception:
            print(DIM + traceback.format_exc() + RESET, end='')
            print(RED + f"Could not load '{ext}'" + RESET)
            return

    for table in Table.all_tables():
        try:
            run(table.create(pool, verbose=not quiet))
        except Exception:
            print(DIM + traceback.format_exc() + RESET, end='')
            print(RED + f"Could not create table '{table.__table_name__}'" + RESET)
        else:
            click.echo(GREEN + f"[{table.__module__}] Created table '{table.__table_name__}'" + RESET)


if __name__ == '__main__':
    main()
