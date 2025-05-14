# miet_schedule_api.py
import requests
import json
from urllib.parse import quote
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any  # Для подсказок типов

# Константы
BASE_URL = "https://miet.ru/schedule"
SCHEDULE_START_DATE_STR = "2025-01-06"  # Понедельник

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
            # Можно добавить более детальную обработку ошибок сервера
            raise MietNetworkError(
                f"HTTP ошибка при запросе к {url}: {e.response.status_code} - {e.response.text}"
            ) from e
        except requests.exceptions.RequestException as e:
            raise MietNetworkError(f"Ошибка сети при запросе к {url}: {e}") from e
        except json.JSONDecodeError as e:
            # Если сервер вернул не JSON
            raise MietApiError(
                f"Ошибка декодирования JSON ответа от {url}: {e}. Ответ: {response.text[:200]}..."
            ) from e

    def get_all_groups(self) -> Optional[List[str]]:
        """Получает список всех групп с сайта МИЭТ."""
        try:
            return self._request("GET", "groups")
        except MietScheduleError as e:
            print(f"Ошибка при получении списка групп: {e}")
            return None

    def get_schedule_for_group(self, group_name: str) -> Optional[Dict[str, Any]]:
        """
        Получает расписание для указанной группы.
        Возвращает полный JSON-объект ответа.
        """
        # Кодируем имя группы для POST-запроса
        payload_str = f"group={quote(group_name.encode('utf-8'))}"
        # requests.post с параметром `data` автоматически установит Content-Type
        # application/x-www-form-urlencoded если data - строка или словарь.
        # Но мы уже добавили его в HEADERS, так что все ок.
        try:
            return self._request("POST", "data", data=payload_str)
        except MietScheduleError as e:
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

        start_of_target_week = target_date - timedelta(days=target_date.weekday())
        start_of_start_date_week = start_date_obj - timedelta(
            days=start_date_obj.weekday()
        )

        week_diff = (start_of_target_week - start_of_start_date_week).days // 7
        return week_diff % 4

    @staticmethod
    def get_week_text_by_day_number(day_number_val: int) -> str:
        """Возвращает текстовое описание недели по ее номеру (0-3)."""
        if day_number_val == 0:
            return "1-й числитель"
        elif day_number_val == 1:
            return "1-й знаменатель"
        elif day_number_val == 2:
            return "2-й числитель"
        elif day_number_val == 3:
            return "2-й знаменатель"
        return f"Неизвестная неделя ({day_number_val})"

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


# --- Вспомогательные функции для форматирования и отображения (можно вынести или оставить для примера) ---
def format_schedule_item_info(item: Dict[str, Any]) -> str:
    """Форматирует одну запись расписания для вывода."""
    time_info = item.get("Time", {})
    class_info = item.get("Class", {})
    room_info = item.get("Room", {})

    time_str = time_info.get("Time", "N/A")  # "1 пара"

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
            if len(potential_type) <= 5 and potential_type.isalpha():
                class_type = potential_type
                subject_name = subject_full_name[:start_bracket].strip()

    room = room_info.get("Name", "N/A")
    teacher = class_info.get("Teacher", "N/A")  # Краткое имя

    day_number_val = item.get("DayNumber")
    week_type_str = MietScheduleClient.get_week_text_by_day_number(day_number_val)

    class_type_display = f" [{class_type}]" if class_type else ""

    # Добавим группу в вывод для сценария с преподавателем
    group_name = item.get("Group", {}).get("Name", "N/A")

    return (
        f"{time_str}: {distant_str}{subject_name}{class_type_display} - Ауд: {room}, "
        f"Преп: {teacher} ({week_type_str}) [Группа: {group_name}]"
    )


def display_formatted_schedule(
    schedule_items: List[Dict[str, Any]],
    semestr: str,
    current_week_text: Optional[str] = None,
):
    """Отображает отформатированный список занятий, сгруппированный по дням."""
    if not schedule_items:
        print("Нет занятий для отображения.")
        return

    print(f"\n--- Расписание на {semestr} ---")
    if current_week_text:
        print(f"--- (Неделя: {current_week_text}) ---")

    schedule_by_day = {}
    for item in schedule_items:
        day_code = item.get("Day")
        if day_code not in schedule_by_day:
            schedule_by_day[day_code] = []
        schedule_by_day[day_code].append(item)

    if not schedule_by_day:
        print("Нет занятий для отображения по текущим фильтрам.")
        return

    for day_code in sorted(schedule_by_day.keys()):
        day_name = MietScheduleClient.get_day_string_by_day_code(day_code)
        print(f"\n--- {day_name} ---")

        day_items_sorted = sorted(
            schedule_by_day[day_code], key=lambda x: x.get("Time", {}).get("Code", 0)
        )
        for item in day_items_sorted:
            print(f"  {format_schedule_item_info(item)}")
