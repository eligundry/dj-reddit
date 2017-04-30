from os import environ

import click

from dj_reddit import DjReddit


DJ = DjReddit(interactive=True)


@click.group()
def cli():
    pass


@cli.command()
@click.argument('username')
def get_spotify_token(username):
    token = environ.get('SPOTIPY_TOKEN')

    if not token:
        token = DJ.generate_spotify_token(username)

    print(token)


if __name__ == '__main__':
    cli()
