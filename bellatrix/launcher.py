import contextlib
import logging
import asyncio
import traceback
import importlib
from pathlib import Path

import click
import humanize

import config
from bot import Bellatrix, all_extensions
from utils.database import DatabaseManager


# TODO: Adicionar uma documentação decente.

class RemoveNoise(logging.Filter):
    def __init__(self):
        super().__init__(name='discord.state')

    def filter(self, record: logging.LogRecord):
        if record.levelname == 'WARNING' and 'referencing an unknown' in record.msg:
            return False

        return True

@contextlib.contextmanager
def setup_logging():
    # Criar a past logs/ antes de inicializar o logger.
    path = Path('logs')
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)

    try:
        # __enter__
        logging.getLogger('discord').setLevel(logging.INFO)
        logging.getLogger('discord.http').setLevel(logging.WARNING)
        logging.getLogger('discord.state').addFilter(RemoveNoise())

        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        datetime_format = '%Y-%m-%d %H:%M:%S'

        handler = logging.FileHandler(filename='logs/bellatrix.log', mode='w', encoding='utf-8')
        formatter = logging.Formatter('[{asctime}] [{levelname}] {name}: {message}', datetime_format, style='{')

        handler.setFormatter(formatter)
        logger.addHandler(handler)

        yield
    finally:
        # __exit__
        for handler in logger.handlers:
            handler.close()
            logger.removeHandler(handler)

def run_bot():
    humanize.activate('pt_BR')

    bot = Bellatrix()
    run = bot.loop.run_until_complete

    bot.manager = run(DatabaseManager.from_dsn(config.postgres, loop=bot.loop))
    bot.run(config.token)

@click.group(invoke_without_command=True, options_metavar='[options]')
@click.pass_context
def main(ctx: click.Context):
    '''Inicia o bot.'''
    if ctx.invoked_subcommand is None:
        with setup_logging():
            run_bot()

@main.group(short_help='coisas do banco de dados', options_metavar='[options]')
def db():
    pass

@db.command(short_help='inicializa o banco de dados', options_metavar='[options]')
@click.option('-q', '--quiet', help='output menos detalhado', is_flag=True)
def init(quiet: bool):
    '''Faz a criação do banco de dados para você.'''
    loop = asyncio.get_event_loop()
    run = loop.run_until_complete

    try:
        manager = run(DatabaseManager.from_dsn(config.postgres, loop=loop))
    except Exception:
        return click.echo(f'Could not create PostgreSQL connection pool\n{traceback.format_exc()}', err=True)

    for ext in all_extensions:
        try:
            importlib.import_module(ext)
        except Exception:
            return click.echo(f'Could not load {ext}\n{traceback.format_exc()}', err=True)

    run(manager.initialize())

if __name__ == '__main__':
    main()