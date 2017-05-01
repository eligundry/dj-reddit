import json
import os

from time import sleep

import click

from dj_reddit import DjReddit


@click.group()
def cli():
    pass


@cli.command()
@click.argument('username')
def get_spotify_token(username):
    dj = DjReddit(interactive=True)
    token = os.getenv('SPOTIPY_TOKEN')

    if not token:
        token = dj.generate_spotify_token(username)

    print(token)


@cli.command()
@click.option('--refresh', default=60, type=int,
              help="Time in minutes before station refresh.")
@click.option('--debug', is_flag=True)
@click.argument('stations')
def run_server(stations, refresh, debug):
    dj = DjReddit(debug=debug)
    stations = json.loads(stations)

    for subreddit, playlist_id in stations.items():
        dj.logger.debug("Adding station /r/%s (%s)", subreddit, playlist_id)
        dj.add_station(subreddit, playlist_id, populate=False)

    while True:
        dj.logger.debug("Refreshing all stations")
        dj.refresh_stations()
        dj.logger.debug("Finished refreshing all stations, "
                        "sleeping %s minutes", refresh)
        sleep(60 * refresh)


if __name__ == '__main__':
    cli(auto_envvar_prefix='DJ_REDDIT')
