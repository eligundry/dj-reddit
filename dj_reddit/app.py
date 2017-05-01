import logging
import os
import re

import praw
import spotipy

from spotipy.util import prompt_for_user_token


class DjReddit(object):
    """Class that will interact with Reddit and Spotify to generate playlists.

    This class requires the following environment variables to be set.

    - ``REDDIT_CLIENT_ID``: The app ID generated by creating a Reddit app.
    - ``REDDIT_CLIENT_SECRET``: The app secret generated by creating a Reddit
        app.
    - ``REDDIT_USERNAME``: Your personal Reddit username.
    - ``REDDIT_PASSWORD``: Your personal Reddit password.
    - ``SPOTIPY_CLIENT_ID``: The ID generated by the Spotify app.
    - ``SPOTIPY_CLIENT_SECRET``: The secret generated by the Spotify app.
    - ``SPOTIPY_USERNAME``: The name of the user to create the playlists for.
    - ``SPOTIPY_TOKEN``: The user token generated by
        ``DjReddit.generate_token``.
    - ``SPOTIPY_REDIRECT_URI``: The URL that Spotify is going to redirect to
        as a part of it's auth flow. This can be hardcoded to
        ``http://localhost:8000`` and ``python -m http.server`` can be run to
        get this token.

    """

    SPOTIFY_SCOPE = 'playlist-modify-public'
    TITLE_REGEX = re.compile(
        r'('
        # Featuring will throw off Spotify searches
        r'(featuring|feat|ft)\.?|'
        # Don't care about some special chars
        r'(&|-|,)'
        r')',
        re.IGNORECASE
    )

    def __init__(self, interactive=False, debug=False):
        self._init_logging(level=logging.DEBUG if debug else logging.WARNING)
        self.max_size = 100
        self.interactive = interactive
        self.reddit = self._create_reddit()
        self.spotify = self._create_spotify()
        self.stations = {}

    def _create_reddit(self):
        """Create a Reddit object and authenticate it.

        Returns:
            praw.Reddit: An authenticated Reddit object.

        """
        self.logger.debug("Authenticating with Reddit...")

        reddit = praw.Reddit(
            client_id=os.environ['REDDIT_CLIENT_ID'],
            client_secret=os.environ['REDDIT_CLIENT_SECRET'],
            username=os.environ['REDDIT_USERNAME'],
            password=os.environ['REDDIT_PASSWORD'],
            user_agent=os.environ.get('REDDIT_USER_AGENT', 'DJ Reddit')
        )

        # This app should never need to write to Reddit
        reddit.read_only = True

        self.logger.debug("Successfully authenticated with Reddit.")

        return reddit

    def _create_spotify(self, token=os.environ.get('SPOTIPY_TOKEN')):
        """Create a Spotify object and authenticate it.

        Returns:
            spotipy.Spotify: An authenticated Spotify API object.

        """
        if not token:
            token = self.generate_spotify_token(os.environ['SPOTIPY_USERNAME'])

        return spotipy.Spotify(auth=token)

    def _reauth_spotify(self):
        self.spotify._auth = prompt_for_user_token(
            os.environ['SPOTIPY_USERNAME'],
            self.SPOTIFY_SCOPE
        )
        os.environ['SPOTIPY_TOKEN'] = self.spotify._auth

    # @TODO Spin up a small web app to get the token from the redirect
    # automatically?
    def generate_spotify_token(self, username):
        """Generate a Spotify token for the account to write the playlist to.

        Args:
            username (str): The name of the user to generate the token for.

        Returns:
            str: The token generated as a part of the authentication flow.

        Raises:
            RuntimeError: This is raised if this class was initialized with
                ``interactive`` equal to ``False``. Because authentication
                requires user interaction in the web browser, this must be run
                from the local shell.

        """
        if not self.interactive:
            raise RuntimeError(
                "The app needs to launch a web browser to complete this token "
                "generation, but this class was initialized in a "
                "non-interactive mode. Try running dj.py's "
                "generate_spotify_token command from your local shell."
            )

        return prompt_for_user_token(username, self.SPOTIFY_SCOPE)

    def add_station(self, subreddit, playlist_id, populate=True):
        self.stations[subreddit] = playlist_id

        if populate:
            self.refresh_station(subreddit)

    def refresh_stations(self):
        for subreddit in self.stations:
            self.refresh_station(subreddit)

    def refresh_station(self, subreddit):
        spotify_uris = []
        playlist_id = self.stations[subreddit]
        sub_model = self.reddit.subreddits.search_by_name(subreddit)[0]
        posts = sub_model.hot()

        # @TODO How do I paginate?
        # while len(spotify_uris) != self.max_size:
        for post in posts:
            media = post.media

            if not media:
                continue

            # We have a Spotify track link, no need to search
            if 'spotify' in media['type'] and 'track' in post.url:
                spotify_uris.append(post.url)
                continue

            track_id = self._get_spotify_id_from_title(
                media['oembed']['title']
            )

            if track_id:
                spotify_uris.append(track_id)

        # Mass add all the tracks to the playlist after it has been cleared.
        self._clear_spotify_playlist(playlist_id)
        self._add_tracks_to_spotify_playlist(playlist_id, spotify_uris)

    def _add_tracks_to_spotify_playlist(self, playlist_id, uris):
        try:
            self.spotify.user_playlist_add_tracks(
                os.environ['SPOTIPY_USERNAME'],
                playlist_id,
                uris,
            )
        except spotipy.SpotifyException:
            self._reauth_spotify()
            self._add_tracks_to_spotify_playlist(playlist_id, uris)

    def _clear_spotify_playlist(self, playlist_id):
        try:
            tracks = self.spotify.user_playlist(
                os.environ['SPOTIPY_USERNAME'],
                playlist_id,
                fields='tracks.items(track(id))'
            )
            track_ids = [t['track']['id'] for t in tracks['tracks']['items']]
            self.spotify.user_playlist_remove_all_occurrences_of_tracks(
                os.environ['SPOTIPY_USERNAME'],
                playlist_id,
                track_ids
            )
        except spotipy.SpotifyException:
            self._reauth_spotify()
            self._clear_spotify_playlist(playlist_id)

    # @TODO Overhaul this with some basic AI.
    # https://textblob.readthedocs.io/
    # https://github.com/seatgeek/fuzzywuzzy
    # I should be able to join the ngrams of the title, loop through the track
    # names, and then use fuzzywuzzy to find the most similar title.
    def _get_spotify_id_from_title(self, title):
        title = self._clean_up_title(title)

        try:
            res = self.spotify.search(q=title, type='track')
        except spotipy.SpotifyException:
            self._reauth_spotify()
            return self._get_spotify_id_from_title(title)

        if not res['tracks']['total']:
            self.logger.debug("Couldn't find track for '{}'".format(title))
            return False

        track_id = res['tracks']['items'][0]['id']

        self.logger.debug('Found track {} for "{}"'.format(track_id, title))

        return track_id

    @classmethod
    def _clean_up_title(cls, title):
        title = re.sub(cls.TITLE_REGEX, ' ', title)
        return ' '.join(title.split())

    def _init_logging(self, level=logging.WARNING):
        # Create a custom logger for this app
        self.logger = logging.getLogger('dj_reddit')
        self.logger.setLevel(level)

        # Log to the console by default
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        self.logger.addHandler(console_handler)
