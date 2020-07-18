import json

from config import SPELLER_URL


async def correct_text(text, session):
    """ Исправляет орфографические ошибки в запросе, используя Яндекс.Спеллер.
        Заменяет слова с ошибками на самый популярный вариант исправления.
        Помимо исправленного текста возвращает флаг был ли текст исправлен или нет."""
    async with session.get(SPELLER_URL + text) as resp:
        corrections = await resp.read()
        corrections = json.loads(corrections[10:-1])
        offset = 0
        for correction in corrections:
            print(correction)
            if len(correction['s']) != 0:
                text = text[:correction['pos'] + offset] + correction['s'][0] + \
                       text[correction['pos'] + correction['len'] + offset:]
                offset += len(correction['s'][0]) - correction['len']
        return text, len(corrections) != 0
