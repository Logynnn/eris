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

from math import log10, floor
from typing import Union


NUMBER_SUFFIXES = ['', 'K', 'M', 'B', 'T']


def _format_number(n: int) -> Union[int, float]:
    '''Formata o número em :class:`int` caso seja divisível por 0.
    Essencialmente, esse código transforma um :class:`float` em
    um :class:`int` caso ele tenha um ponto decimal 0. Por exemplo:

    ```pycon
    >>> _format_number(52.2)
    52.2
    >>> _format_number(7.0)
    7
    ```

    Parameters
    ----------
    n: :class:`int`
        O número a ser formatado.

    Returns
    -------
    Union[:class:`int`, :class:`float`]
        O número formatado.
    '''    
    return n if n % 1 else int(n)


def suffix_number(n: int, *, ends: list[str] = NUMBER_SUFFIXES) -> str:
    '''Reduz o número usando sufixos de grandezas.
    Exemplo:
    ```pycon
    >>> suffix_number(100_000)
    100K
    >>> suffix_number(54_200_000)
    54.2M
    ```

    Caso o número seja menor ou igual a `0` então
    o próprio número é retornado.

    Parameters
    ----------
    n: :class:`int`
        O número a ter o sufixo atribuido.
    ends: list[:class:`str`]
        A lista de sufixos a serem usados, por padrão é
        `['', 'K', 'M', 'B', 'T']`.

    Returns
    -------
    :class:`str`
        O número formatado com o sufixo.
    '''
    if n <= 0:
        return str(n)

    index = int(floor(log10(n)) / 3)
    divide = 1000 ** index
    
    num = round(_format_number(n / divide), 2)
    return f'{num}{ends[index]}'
