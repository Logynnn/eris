import discord


# Isso é um construtor customizado para ``Embed``s. Serve pra facilitar a criação dos mesmos.
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