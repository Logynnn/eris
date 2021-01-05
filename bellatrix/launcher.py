import contextlib
import logging

import config
from bot import Bellatrix


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
    bot = Bellatrix()
    bot.run(config.token)

def main():
    '''Inicia o bot.'''
    with setup_logging():
        run_bot()

if __name__ == '__main__':
    main()