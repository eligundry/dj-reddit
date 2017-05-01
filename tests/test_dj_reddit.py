import pytest

from dj_reddit import DjReddit


@pytest.mark.parametrize('title,result', (
    ('Jeremih - I Think Of You ft. Chris Brown, Big Sean',
     'Jeremih I Think Of You Chris Brown Big Sean'),
    ('Curren$y - Ballin Starvin',
     'Curren$y Ballin Starvin'),
    ('Lil Yachty - And I Made It (feat. Just Juice)',
     'Lil Yachty And I Made It'),
    ('Slum Village Featuring Kanye West & John Legend - Selfish',
     'Slum Village Kanye West John Legend Selfish')
))
def test_title_cleaning(title, result):
    assert DjReddit._clean_up_title(title) == result
