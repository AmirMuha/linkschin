"""Movie and series scraper plugins.

Each module is a standalone plugin depending on no sibling scraper (Constitution I);
shared behaviour comes only from `sources.base` and `sources.movies.base_movie`.
"""

from sources.movies.aparat import AparatPlugin
from sources.movies.babakfilm import BabakFilmPlugin
from sources.movies.danfilo import DanfiloPlugin
from sources.movies.digitoon import DigitoonPlugin
from sources.movies.doostihaa import DoostihaaPlugin
from sources.movies.fam import FamPlugin
from sources.movies.filimo import FilimoPlugin
from sources.movies.filmchiin import FilmChiinPlugin
from sources.movies.filmnet import FilmnetPlugin
from sources.movies.filmtarin import FilmTarinPlugin
from sources.movies.gapfilm import GapfilmPlugin
from sources.movies.imvbox import IMVBoxPlugin
from sources.movies.namasha import NamashaPlugin
from sources.movies.namava import NamavaPlugin
from sources.movies.ndamedia import NdaMediaPlugin
from sources.movies.rubika import RubikaPlugin
from sources.movies.salamcinema import SalamCinemaPlugin
from sources.movies.sarvnema import SarvnemaPlugin
from sources.movies.telewebion import TelewebionPlugin
from sources.movies.tiwall import TiwallPlugin
from sources.movies.uptvs import UpTVsPlugin

__all__ = [
    "AparatPlugin",
    "BabakFilmPlugin",
    "DanfiloPlugin",
    "DigitoonPlugin",
    "DoostihaaPlugin",
    "FamPlugin",
    "FilimoPlugin",
    "FilmChiinPlugin",
    "FilmnetPlugin",
    "FilmTarinPlugin",
    "GapfilmPlugin",
    "IMVBoxPlugin",
    "NamashaPlugin",
    "NamavaPlugin",
    "NdaMediaPlugin",
    "RubikaPlugin",
    "SalamCinemaPlugin",
    "SarvnemaPlugin",
    "TelewebionPlugin",
    "TiwallPlugin",
    "UpTVsPlugin",
]
