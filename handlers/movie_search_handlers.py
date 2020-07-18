import aiogram
import aiohttp
import googlesearch as google
import tmdbsearch as tmdb

from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from main import dp
from features import correct_text
from operator import itemgetter
from states.movie_search_states import MovieSearch
from urllib import parse

from config import ADDITIONAL, BASE_URL_IMAGE, FILE_SIZE, TMDB_API_KEY, GOOGLE, LINK_FOUND_TEXT, LINK_NOT_FOUND_TEXT

tmdb.API_KEY = TMDB_API_KEY


@dp.message_handler(Command(['поиск', 's', 'search']), state=None)
async def proposal_search_movie(message: types.Message):
    await message.answer("Какой фильм вы хотели бы найти? Если хотите указать год выпуска, "
                         "то добавьте его к названию через @, например \"Мстители@2012\"")
    await MovieSearch.QueryEntering.set()


@dp.message_handler(state=MovieSearch.QueryEntering)
async def query_entering(message: types.Message, state: FSMContext):
    """ Исправляем ошибки в запросе """
    text, year = message.text, None
    try:
        text, year = message.text.split("@")
        print("TEXT", text)
        print("YEAR", year)
    except Exception:
        pass
    async with aiohttp.ClientSession() as session:
        corrected_message, was_corrected = await correct_text(text, session)
        if was_corrected:
            await state.update_data({"corrected_query": corrected_message,
                                     "row_query": text, "index": 0, "year": year})
            await message.answer(f"Вы имели в виду \"{corrected_message}\"? [Да/Нет]")
            return await MovieSearch.QueryCorrectness.set()
        await state.update_data({"query": text, "index": 0, "year": year})
        await MovieSearch.RequestCorrectness.set()
        await find_movie_info(message, state)


async def send_movie_info(message, state):
    data = await state.get_data()
    movie_list, year, index, genres = data.get("movie_list"), data.get("year"), \
                                      data.get("index"), data.get("genres")
    if year is not None:
        print(year, movie_list[0]["release_date"], index)
        movie_list = [movie for movie in movie_list if year in movie['release_date']]
        print(movie_list)
    if len(movie_list) > index:
        movie = movie_list[index]
        movie = movie_list[index]
        reply_text = f"<b>{movie['title']}</b> ({movie['release_date'][:4]})\n" + \
                     f"Средня оценка: {movie['vote_average']}\n" + \
                     f"Жанры: {', '.join([genres[idx] for idx in movie['genre_ids']])}\n"
        if movie['overview'] is not None:
            reply_text += f"Описание: {movie['overview']}\n"
    else:
        await message.answer(f"Фильмов не найдено, попробуйте еще раз")
        return await MovieSearch.QueryEntering.set()

    media = types.MediaGroup()
    if movie['poster_path'] is not None:
        print(BASE_URL_IMAGE + FILE_SIZE + movie['poster_path'])
        media.attach_photo(BASE_URL_IMAGE + FILE_SIZE + movie['poster_path'], reply_text)
        # TODO иногда выдает aiogram.utils.exceptions.BadRequest: Wrong type of the web page content
        try:
            await message.answer_media_group(media=media)
        except aiogram.utils.exceptions.BadRequest:
            await message.answer(reply_text)
    else:
        await message.answer(reply_text)
    await state.update_data(movie_list=movie_list)

    link, status = await get_movie_link(movie)
    keyboard = aiogram.types.InlineKeyboardMarkup()

    if status:
        button = aiogram.types.InlineKeyboardButton(text="Смотреть", url=link)
        keyboard.add(button)
        await message.answer("Ссылка на фильм", reply_markup=keyboard)
    else:
        button = aiogram.types.InlineKeyboardButton(text="Искать", url=link)
        keyboard.add(button)
        await message.answer("Найти в Google?", reply_markup=keyboard)

    await message.answer("Это то, что вы искали? [Да/Нет]")
    await MovieSearch.MovieCorrectness.set()


async def find_movie_info(message: types.Message, state: FSMContext):
    """ Ищем фильм, если запрос верный, иначе предлагаем ввести запрос еще раз """

    data = await state.get_data()
    query = data.get("query")
    search = tmdb.TMDB()
    async with aiohttp.ClientSession() as session:
        await search.movie_list(session)
        await search.movie(session=session, query=query, language='ru')

    movie_list = sorted(search.results, key=itemgetter('vote_average'), reverse=True)
    # movie_list = search.results
    await state.update_data({"movie_list": movie_list, "genres": search.GENRES})
    await send_movie_info(message, state)




@dp.message_handler(state=MovieSearch.QueryCorrectness)
async def query_correctness(message: types.Message, state: FSMContext):
    """Если исправления корректны, то ищем по исправленному запросу. Иначе по исходному"""
    data = await state.get_data()
    corrected_query, row_query = data.get("corrected_query"), data.get("row_query")

    if message.text.lower().strip() in ["да", "yes", "конечно"]:
        await state.update_data({"query": corrected_query})
        await MovieSearch.RequestCorrectness.set()
        await find_movie_info(message, state)
    elif message.text.lower().strip() in ["нет", "no"]:
        await state.update_data({"query": row_query})
        await MovieSearch.RequestCorrectness.set()
        await find_movie_info(message, state)
    else:
        await message.answer("Чтож, давайте начнем все сначала")
        await state.finish()
        await proposal_search_movie()



@dp.message_handler(state=MovieSearch.MovieCorrectness)
async def movie_correctness(message: types.Message, state: FSMContext):
    """ Спрашиваем правильный ли фильм мы показали. Если да, то спршиваем нужна ли ссылка
        для просмотра. Если нет, то показываем список кандидатов."""
    if message.text.lower().strip() in ["да", "yes", "конечно"]:
        await message.answer(LINK_FOUND_TEXT)
        await state.finish()
    elif message.text.lower().strip() in ["нет", "no"]:

        await message.answer("Извините, я исправлюсь. Подскажите, какой фильм вас интересует. "
                             "[Номер. 0, если ничего не подходит]")
        data = await state.get_data()
        movie_list, index, genres = data.get("movie_list"), data.get("index"), data.get("genres")
        reply = ""
        for idx, movie in enumerate(movie_list):
            reply += f"<b>{idx + 1}. {movie['title']}</b> ({movie['release_date'][:4]})\n" + \
                     f"Средняя оценка: {movie['vote_average']}\n" + \
                     f"Жанры: {', '.join([genres[idx] for idx in movie['genre_ids']])}\n\n"
        await message.answer(reply)
        await MovieSearch.NumberEntering.set()
    else:
        await message.answer("Чтож, давайте начнем все сначала")
        await proposal_search_movie(message)
    

@dp.message_handler(state=MovieSearch.NumberEntering)
async def number_entering(message: types.Message, state: FSMContext):
    try:
        index = int(message.text) - 1
    except Exception:
        return await message.answer("Некорректный номер, введите число еще раз")

    if index == -1:
        await message.answer("Эх, может быть в другой раз.")
        await state.finish()
    else:
        data = await state.get_data()
        movie_list = data.get("movie_list")
        await state.update_data(index=index)
        await send_movie_info(message, state)

# def filter_link(link):
#     bad_cinemas = ["kinopoisk", "wikipedia", "ivi", "okko", "megogo", "youtube"]
#     for bad_cinema in bad_cinemas:
#         if bad_cinema in link:
#             return False
#     return True


async def get_movie_link(movie):
    """ Ищем ссылку для просмотра. Возвращаем ссылку и True в случае успеха.
        В случае неудачи возвращаем ссылку с поисковым запросов в гугл и False """
    async with aiohttp.ClientSession() as session:

        search_results = await google.search(" ".join([movie['title'], movie['release_date'][:4], ADDITIONAL]),
                                             session)
        for search_result in search_results:
            async with session.get(search_result.link) as resp:
                if resp.status == 200:
                    return search_result.link, True
        return GOOGLE + " ".join([movie['title'], movie['release_date'][:4], ADDITIONAL]), False


@dp.message_handler(state=MovieSearch.NeedLink)
async def need_link(message: types.Message, state: FSMContext):
    if message.text.lower().strip() in ["да", "yes", "конечно"]:
        data = await state.get_data()
        movie_list, index = data.get("movie_list"), data.get("index")
        link, status = get_movie_link(movie_list[index])

        reply = status * LINK_FOUND_TEXT + (not status) * LINK_NOT_FOUND_TEXT

        keyboard = aiogram.types.InlineKeyboardMarkup()
        button = aiogram.types.InlineKeyboardButton(text="Смотреть", url=link)
        keyboard.add(button)
        await message.answer(reply, reply_markup=keyboard)
        await state.finish()
    elif message.text.lower().strip() in ["нет", "no"]:
        await message.answer("Хорошо, обращайтесь ещё")
        await state.finish()
    else:
        await message.answer("Чтож, давайте начнем все сначала")
        await proposal_search_movie(message)


@dp.message_handler(state=None)
async def echo(message: types.Message):
    await message.answer("Я всего лишь бот, который помогает искать кино. "
                         "Воспользуйтесь, пожалуйста, командой /help, чтобы узнать о моих возможностях.")
