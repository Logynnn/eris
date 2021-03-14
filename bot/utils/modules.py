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

import os
import re


def get_all_extensions(path: str = 'extensions/') -> list[str]:
    '''Retorna a lista de extensões do `path` indicado.

    Parameters
    ----------
    path: Optional[class:`str`]
        O caminho para procurar extensões, por padrão `extensions/`.

    Returns
    -------
    list[str]
        A lista de extensões encontradas.
    '''                
    extensions = []

    for root, dirs, files in os.walk(path):
        for file in files:
            path = os.path.join(root, file)

            if not os.path.isfile(path):
                continue

            path, ext = os.path.splitext(path)
            if ext != '.py':
                continue

            extensions.append(re.sub(r'\\|\/', '.', path))

    return extensions
