# miet_schedule_api.py
import json
from datetime import datetime, timedelta
from typing import (  # Добавил Callable для будущей гибкости, если понадобится
    Any, Callable, Dict, List, Optional)
from urllib.parse import quote

import requests

# Константы
BASE_URL = "https://miet.ru/schedule"
SCHEDULE_START_DATE_STR = (
    "2025-01-06"  # Понедельник (Примерная дата, установите актуальную)
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://miet.ru",
    "Referer": "https://miet.ru/schedule/",
    "DNT": "1",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}


class MietScheduleError(Exception):
    """Базовый класс для ошибок этого API клиента."""

    pass


class MietNetworkError(MietScheduleError):
    """Ошибка сети при запросе к API МИЭТ."""

    pass


class MietApiError(MietScheduleError):
    """Ошибка от API МИЭТ (например, неверный формат ответа)."""

    pass


class MietScheduleClient:
    def __init__(self, session: Optional[requests.Session] = None):
        """
        Инициализирует клиент.
        :param session: Опциональная сессия requests для повторного использования соединений.
        """
        self.session = session or requests.Session()
        self.session.headers.update(HEADERS)  # Устанавливаем заголовки для сессии

    def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Внутренний метод для выполнения запросов."""
        url = f"{BASE_URL}/{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()  # Вызовет исключение для 4xx/5xx ошибок
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_text = e.response.text if e.response else "Нет тела ответа"
            raise MietNetworkError(
                f"HTTP ошибка при запросе к {url}: {e.response.status_code if e.response else 'N/A'} - {error_text}"
            ) from e
        except requests.exceptions.RequestException as e:
            raise MietNetworkError(f"Ошибка сети при запросе к {url}: {e}") from e
        except json.JSONDecodeError as e:
            # Если сервер вернул не JSON
            # 'response' может быть не определена, если ошибка произошла до получения ответа
            resp_text = kwargs.get("response", None)
            if resp_text and hasattr(resp_text, "text"):
                resp_text_snippet = resp_text.text[:200]
            else:
                resp_text_snippet = "Ответ не получен или не содержит текст"
            raise MietApiError(
                f"Ошибка декодирования JSON ответа от {url}: {e}. Ответ: {resp_text_snippet}..."
            ) from e

    def get_all_groups(self) -> Optional[List[str]]:
        """Получает список всех групп с сайта МИЭТ."""
        try:
            return self._request("GET", "groups")
        except MietScheduleError as e:
            # Можно логировать ошибку или обрабатывать специфичнее
            print(f"Ошибка при получении списка групп: {e}")
            return None

    def get_schedule_for_group(self, group_name: str) -> Optional[Dict[str, Any]]:
        """
        Получает расписание для указанной группы.
        Возвращает полный JSON-объект ответа.
        """
        payload_str = f"group={quote(group_name.encode('utf-8'))}"
        try:
            return self._request("POST", "data", data=payload_str)
        except MietScheduleError as e:
            # Можно логировать ошибку или обрабатывать специфичнее
            print(f"Ошибка при получении расписания для группы {group_name}: {e}")
            return None

    @staticmethod
    def get_current_week_day_number(target_date: Optional[datetime] = None) -> int:
        """
        Вычисляет номер текущей недели (0-3) для указанной даты.
        0: 1-й числитель, 1: 1-й знаменатель, 2: 2-й числитель, 3: 2-й знаменатель.
        """
        if target_date is None:
            target_date = datetime.now()

        start_date_obj = datetime.strptime(SCHEDULE_START_DATE_STR, "%Y-%m-%d")

        # Приводим обе даты к началу их недель (понедельнику)
        start_of_target_week = target_date - timedelta(days=target_date.weekday())
        start_of_start_date_week = start_date_obj - timedelta(
            days=start_date_obj.weekday()
        )

        week_diff = (start_of_target_week - start_of_start_date_week).days // 7
        return week_diff % 4

    @staticmethod
    def get_week_text_by_day_number(day_number_val: int) -> str:
        """Возвращает текстовое описание недели по ее номеру (0-3)."""
        week_map = {
            0: "1-й числитель",
            1: "1-й знаменатель",
            2: "2-й числитель",
            3: "2-й знаменатель",
        }
        return week_map.get(day_number_val, f"Неизвестная неделя ({day_number_val})")

    @staticmethod
    def get_day_string_by_day_code(day_code: int) -> str:
        """Возвращает строковое представление дня недели по его коду (1-7)."""
        days_map = {
            1: "Понедельник",
            2: "Вторник",
            3: "Среда",
            4: "Четверг",
            5: "Пятница",
            6: "Суббота",
            7: "Воскресенье",
        }
        return days_map.get(day_code, f"День {day_code}")

    @staticmethod
    def get_pair_time_info(
        lessons_data: List[Dict[str, Any]],
        pair_identifier: Any,  # Может быть int (код пары) или str ("1 пара")
    ) -> Optional[Dict[str, Optional[str]]]:
        """
        Находит информацию о времени (TimeFrom, TimeTo) для указанной пары
        из предоставленного списка данных о занятиях.
        Ищет первое совпадение.
        """
        if not lessons_data:
            return None

        for lesson in lessons_data:
            time_data = lesson.get("Time")
            if not isinstance(time_data, dict):
                continue

            match_found = False
            if (
                isinstance(pair_identifier, int)
                and time_data.get("Code") == pair_identifier
            ):
                match_found = True
            elif (
                isinstance(pair_identifier, str)
                and time_data.get("Time") == pair_identifier
            ):
                match_found = True

            if match_found:
                return {
                    "TimeFrom": time_data.get("TimeFrom"),
                    "TimeTo": time_data.get("TimeTo"),
                }
        return None


# --- Вспомогательные функции для форматирования и отображения ---


def _default_format_schedule_item(item: Dict[str, Any]) -> str:
    """
    Базовая функция форматирования одной записи расписания.
    Включает время начала и конца пары.
    """
    time_data = item.get("Time", {})
    class_info = item.get("Class", {})
    room_info = item.get("Room", {})

    pair_text = time_data.get("Time", "N/A")  # "1 пара"
    time_from = time_data.get("TimeFrom", "")  # "09:00"
    time_to = time_data.get("TimeTo", "")  # "10:20"

    time_str_display = pair_text
    if time_from and time_to:
        time_str_display = f"{pair_text} ({time_from}-{time_to})"
    elif time_from:  # Если есть только время начала
        time_str_display = f"{pair_text} (с {time_from})"
    elif time_to:  # Если есть только время конца (маловероятно, но для полноты)
        time_str_display = f"{pair_text} (до {time_to})"
    # Если нет ни TimeFrom, ни TimeTo, останется просто pair_text

    subject_full_name = class_info.get("Name", "N/A")
    is_distant = class_info.get("Form", False)
    distant_str = ""

    if is_distant:
        distant_str = "[ДСТ] "
        if subject_full_name.startswith("[ДСТ]"):
            subject_full_name = subject_full_name[len("[ДСТ]") :].lstrip()

    class_type = ""
    subject_name = subject_full_name
    if "[" in subject_full_name and "]" in subject_full_name:
        start_bracket = subject_full_name.rfind("[")
        end_bracket = subject_full_name.rfind("]")
        if start_bracket != -1 and end_bracket != -1 and start_bracket < end_bracket:
            potential_type = subject_full_name[start_bracket + 1 : end_bracket]
            if (
                len(potential_type) <= 5
                and potential_type.isalpha()
                and potential_type.upper() == potential_type
            ):  # Тип обычно в верхнем регистре
                class_type = potential_type
                subject_name = subject_full_name[:start_bracket].strip()

    room = room_info.get("Name", "N/A")
    teacher = class_info.get("Teacher", "N/A")  # Краткое имя

    day_number_val = item.get("DayNumber")  # Это номер недели (0-3)
    week_type_str = MietScheduleClient.get_week_text_by_day_number(day_number_val)

    class_type_display = f" [{class_type}]" if class_type else ""

    group_name_info = item.get("Group", {})  # Безопасное извлечение
    group_name = group_name_info.get("Name", "N/A") if group_name_info else "N/A"

    return (
        f"{time_str_display}: {distant_str}{subject_name}{class_type_display} - Ауд: {room}, "
        f"Преп: {teacher} ({week_type_str}) [Группа: {group_name}]"
    )


def display_formatted_schedule(
    schedule_items: List[Dict[str, Any]],
    semestr: str,
    current_week_text: Optional[str] = None,
    item_formatter: Callable[[Dict[str, Any]], str] = _default_format_schedule_item,
):
    """Отображает отформатированный список занятий, сгруппированный по дням."""
    if not schedule_items:
        # Это сообщение может быть избыточным, если фильтрация происходит до вызова.
        # print("Нет занятий для отображения.")
        return

    print(f"\n--- Расписание на {semestr} ---")
    if current_week_text:
        print(f"--- (Неделя: {current_week_text}) ---")

    schedule_by_day: Dict[int, List[Dict[str, Any]]] = {}
    for item in schedule_items:
        day_code = item.get("Day")
        if day_code is None:  # Пропускаем занятия без указания дня
            continue
        if day_code not in schedule_by_day:
            schedule_by_day[day_code] = []
        schedule_by_day[day_code].append(item)

    if not schedule_by_day:
        # Это сообщение актуально, если schedule_items не пуст,
        # но после группировки по дням (или из-за фильтра day_code is None) ничего не осталось.
        print(
            "Нет занятий для отображения по текущим фильтрам (возможно, не указаны дни)."
        )
        return

    for day_code in sorted(schedule_by_day.keys()):
        day_name = MietScheduleClient.get_day_string_by_day_code(day_code)
        print(f"\n--- {day_name} ---")

        # Сортировка занятий внутри дня по их коду времени
        day_items_sorted = sorted(
            schedule_by_day[day_code], key=lambda x: x.get("Time", {}).get("Code", 0)
        )
        for item in day_items_sorted:
            print(f"  {item_formatter(item)}")


# Пример использования (можно закомментировать или удалить, если модуль только для импорта)
if __name__ == "__main__":
    client = MietScheduleClient()

    # 1. Получение списка всех групп
    # all_groups = client.get_all_groups()
    # if all_groups:
    #     print("Доступные группы:", all_groups[:5]) # Первые 5 для примера
    # else:
    #     print("Не удалось получить список групп.")

    # 2. Получение расписания для конкретной группы
    test_group = "ИВТ-13"  # Измените на нужную группу
    print(f"\nЗапрос расписания для группы: {test_group}")
    schedule_data = client.get_schedule_for_group(test_group)

    if schedule_data:
        lessons = schedule_data.get("Data", [])
        semestr = schedule_data.get("Semestr", "Текущий семестр")

        # Определение текущей недели для фильтрации (показываем только одну неделю для примера)
        current_week_num = MietScheduleClient.get_current_week_day_number()
        current_week_text_for_display = MietScheduleClient.get_week_text_by_day_number(
            current_week_num
        )

        print(f"Фильтруем расписание для недели: {current_week_text_for_display}")

        filtered_lessons_for_current_week = [
            lesson for lesson in lessons if lesson.get("DayNumber") == current_week_num
        ]

        if filtered_lessons_for_current_week:
            display_formatted_schedule(
                filtered_lessons_for_current_week,
                semestr,
                current_week_text_for_display,
            )
        else:
            print(
                f"Нет занятий для группы {test_group} на неделе '{current_week_text_for_display}'."
            )

        # Пример использования get_pair_time_info
        if lessons:
            time_info = MietScheduleClient.get_pair_time_info(lessons, "1 пара")
            if time_info:
                print(
                    f"\nВремя для '1 пары' (первое найденное): {time_info['TimeFrom']} - {time_info['TimeTo']}"
                )

            time_info_code = MietScheduleClient.get_pair_time_info(
                lessons, 2
            )  # для "2 пары"
            if time_info_code:
                print(
                    f"Время для пары с кодом 2: {time_info_code['TimeFrom']} - {time_info_code['TimeTo']}"
                )

    else:
        print(f"Не удалось получить расписание для группы {test_group}.")

    # 3. Пример вычисления номера недели для конкретной даты
    # custom_date = datetime(2025, 1, 13) # Пример, Понедельник
    # week_num_for_custom_date = MietScheduleClient.get_current_week_day_number(custom_date)
    # week_text_for_custom_date = MietScheduleClient.get_week_text_by_day_number(week_num_for_custom_date)
    # print(f"\nДля даты {custom_date.strftime('%Y-%m-%d')} неделя: {week_text_for_custom_date} (номер {week_num_for_custom_date})")
