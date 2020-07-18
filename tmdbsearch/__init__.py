import os

from .tmdb_search import APIKeyError
from .tmdb_search import TMDB
API_KEY = os.environ.get('TMDB_API_KEY', None)
API_VERSION = '3'