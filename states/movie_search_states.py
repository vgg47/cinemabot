from aiogram.dispatcher.filters.state import StatesGroup, State


class MovieSearch(StatesGroup):
    QueryEntering = State()
    QueryCorrectness = State()
    RequestCorrectness = State()
    MovieCorrectness = State()
    NumberEntering = State()
    NeedLink = State()
    LinkCorrectness = State()
    Gratitude = State()