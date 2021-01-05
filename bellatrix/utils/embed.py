import discord


# Isso é um construtor customizado para ``Embed``s. Serve pra facilitar a criação dos mesmos.
class Embed(discord.Embed):
    def __init__(self, **kwargs):
        options = {
            'fields': {
                'type': list,
                'function': lambda args: map(lambda fields: self.add_field(**fields), args)
            },
            'footer': {
                'type': dict,
                'function': lambda args: self.set_footer(**args)
            },
            'author': {
                'type': dict,
                'function': lambda args: self.set_author(**args)
            },
            'image': {
                'type': str,
                'function': lambda url: self.set_image(url=url)
            },
            'thumbnail': {
                'type': str,
                'function': lambda url: self.set_thumbnail(url=url)
            }
        }

        for option in options:
            embed_attr = kwargs.get(option)
            option_attr = options.get(option)

            if not embed_attr:
                continue

            if not isinstance(embed_attr, option_attr['type']):
                option_type = option_attr['type'].__name__
                embed_type = embed_attr.__name__
                raise TypeError(f'{option} type must be {option_type}, not {embed_type}')

            option_attr['function'](embed_attr)

        super().__init__(**kwargs)