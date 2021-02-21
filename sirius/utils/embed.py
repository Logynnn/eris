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

import discord


# Isso é um construtor customizado para ``Embed``s. Serve pra facilitar a
# criação dos mesmos.
class Embed(discord.Embed):
    def __init__(self, **kwargs):
        options = {
            'fields': lambda args: [self.add_field(**fields) for fields in args],
            'footer': lambda args: self.set_footer(**args),
            'author': lambda args: self.set_author(**args),
            'image': lambda url: self.set_image(url=url),
            'thumbnail': lambda url: self.set_thumbnail(url=url)
        }

        for option in options:
            embed_attr = kwargs.get(option)
            func = options.get(option)

            if not embed_attr:
                continue

            func(embed_attr)

        super().__init__(**kwargs)
