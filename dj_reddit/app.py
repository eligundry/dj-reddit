from os import environ

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

    def __init__(self, interactive=False):
        self.interactive = interactive
        self.reddit = self._create_reddit()
        self.spotify = self._create_spotify()

    def _create_reddit(self):
        """Create a Reddit object and authenticate it.

        Returns:
            praw.Reddit: An authenticated Reddit object.

        """
        reddit = praw.Reddit(
            client_id=environ['REDDIT_CLIENT_ID'],
            client_secret=environ['REDDIT_CLIENT_SECRET'],
            username=environ['REDDIT_USERNAME'],
            password=environ['REDDIT_PASSWORD'],
            user_agent=environ.get('REDDIT_USER_AGENT', 'DJ Reddit')
        )

        # This app should never need to write to Reddit
        reddit.read_only = True

        return reddit

    def _create_spotify(self, token=environ.get('SPOTIPY_TOKEN')):
        """Create a Spotify object and authenticate it.

        Returns:
            spotipy.Spotify: An authenticated Spotify API object.

        """
        if not token:
            token = self.generate_spotify_token(environ['SPOTIPY_USERNAME'])

        return spotipy.Spotify(auth=token)

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

        return prompt_for_user_token(username, 'playlist-modify-public')
