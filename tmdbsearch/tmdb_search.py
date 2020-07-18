from urllib import parse

class APIKeyError(Exception):
    pass

class TMDB(object):
    headers = {'Content-Type': 'application/json',
               'Accept': 'application/json',
               'Connection': 'close'}
    BASE_PATH = 'search'
    URLS = {
        'movie': '/movie',
        'collection': '/collection',
        'tv': '/tv',
        'person': '/person',
        'company': '/company',
        'keyword': '/keyword',
        'multi': '/multi'
    }
    GENRES = []

    def __init__(self):
        from . import API_VERSION
        self.base_uri = 'https://api.themoviedb.org'
        self.base_uri += '/{version}'.format(version=API_VERSION)


    def _get_params(self, params):
        from . import API_KEY
        if not API_KEY:
            raise APIKeyError

        api_dict = {'api_key': API_KEY}
        if params:
            params.update(api_dict)
            for key, value in params.items():
                if isinstance(params[key], bool):
                    params[key] = 'true' if value is True else 'false'

        else:
            params = api_dict
        return params

    def _get_complete_url(self, path, params):
        params = self._get_params(params)
        return '{base_uri}/{path}'.format(base_uri=self.base_uri, path=path) + "?" + \
               parse.urlencode(params)


    async def movie_list(self, session, **params):
        """
        Get the list of Movie genres.
        Args:
            language: (optional) ISO 639-1 code.
        Returns:
            A dict respresentation of the JSON returned from the API.
        """
        params['language'] = "ru-RU"
        url = self._get_complete_url("genre/movie/list", params)
        async with session.get(url) as response:
            genres = await response.json()
        self.GENRES = {elem["id"]: elem["name"] for elem in genres["genres"]}


    async def _set_attrs_to_values(self, response):
        """
        Set attributes to dictionary values.
        - e.g. movie.title  # instead of response['title']
        """
        response = await response.json()
        # print("JSON: ", await response.json())
        if isinstance(response, dict):
            for key in response.keys():
                if not hasattr(self, key) or not callable(getattr(self, key)):
                    setattr(self, key, response[key])


    async def movie(self, session, **params):
        """
        Search for movies by title.
        Args:
            query: CGI escaped string.
            page: (optional) Minimum value of 1. Expected value is an integer.
            language: (optional) ISO 639-1 code.
            include_adult: (optional) Toggle the inclusion of adult titles.
                           Expected value is True or False.
            year: (optional) Filter the results release dates to matches that
                  include this value.
            primary_release_year: (optional) Filter the results so that only
                                  the primary release dates have this value.
            search_type: (optional) By default, the search type is 'phrase'.
                         This is almost guaranteed the option you will want.
                         It's a great all purpose search type and by far the
                         most tuned for every day querying. For those wanting
                         more of an "autocomplete" type search, set this
                         option to 'ngram'.
        Returns:
            A dict respresentation of the JSON returned from the API.
        """
        url = self._get_complete_url('search/movie', params)
        print("URL TMDB: ", url)
        async with session.get(url) as response:
            return await self._set_attrs_to_values(response)
