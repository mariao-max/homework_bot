class TheAnswerIsNot200Error(Exception):
    """Ответ сервера не равен 200."""


class EmptyDictionaryOrListError(Exception):
    """Пустой словарь или список."""


class RequestExceptionError(Exception):
    """Ошибка при запросе."""


class NoDocumentedStatusError(Exception):
    """Недокументированный статус."""


class ResponseIsNone(Exception):
    """Ответ пуст."""
