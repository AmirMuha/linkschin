from models import SearchQuery, SourceConfig, Category, SourceKind
from sources.music.spotify import SpotifyPlugin
from sources.music.youtube_music import YoutubeMusicPlugin
from sources.music.soundcloud import SoundcloudPlugin
from sources.music.namasha import NamashaPlugin
from sources.music.shenoto import ShenotoPlugin
from sources.music.farsichart import FarsiChartPlugin

def test_custom_search_urls():
    query = SearchQuery(raw_query="test query", normalized_query="test query", category=Category.MUSIC)
    
    spotify = SpotifyPlugin(SourceConfig(id="spotify", name="Spotify", category=Category.MUSIC, base_urls=["https://open.spotify.com"], kind=SourceKind.REFERENCE))
    assert spotify.search_url(query) == "https://open.spotify.com/search/test+query"

    yt = YoutubeMusicPlugin(SourceConfig(id="yt", name="YT", category=Category.MUSIC, base_urls=["https://music.youtube.com"], kind=SourceKind.REFERENCE))
    assert yt.search_url(query) == "https://music.youtube.com/search?q=test+query"

    sc = SoundcloudPlugin(SourceConfig(id="sc", name="SC", category=Category.MUSIC, base_urls=["https://soundcloud.com"], kind=SourceKind.REFERENCE))
    assert sc.search_url(query) == "https://soundcloud.com/search?q=test+query"

    namasha = NamashaPlugin(SourceConfig(id="namasha", name="Namasha", category=Category.MUSIC, base_urls=["https://namasha.com"], kind=SourceKind.REFERENCE))
    assert namasha.search_url(query) == "https://namasha.com/search?q=test+query"

    shenoto = ShenotoPlugin(SourceConfig(id="shenoto", name="Shenoto", category=Category.MUSIC, base_urls=["https://shenoto.com"], kind=SourceKind.REFERENCE))
    assert shenoto.search_url(query) == "https://shenoto.com/search?q=test+query"

    farsichart = FarsiChartPlugin(SourceConfig(id="farsichart", name="FarsiChart", category=Category.MUSIC, base_urls=["https://farsichart.com"], kind=SourceKind.REFERENCE))
    assert farsichart.search_url(query) == "https://farsichart.com/?q=test+query"

