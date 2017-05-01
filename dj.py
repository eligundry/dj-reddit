from os import environ

import click

from dj_reddit import DjReddit


@click.group()
def cli():
    pass


@cli.command()
@click.argument('username')
def get_spotify_token(username):
    dj = DjReddit(interactive=True)
    token = environ.get('SPOTIPY_TOKEN')

    if not token:
        token = dj.generate_spotify_token(username)

    print(token)


if __name__ == '__main__':
    cli()
