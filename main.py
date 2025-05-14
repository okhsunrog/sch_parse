# main.py
import requests
import json
from urllib.parse import quote  # Для URL-кодирования имени группы

# Базовый URL для API расписания
BASE_URL = "https://miet.ru/schedule"

# Заголовки, которые могут понадобиться, чтобы запрос выглядел как от браузера
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",  # Пример User-Agent
    "Accept": "application/json, text/javascript, */*; q=0.01",  # Тип ответа, который мы ожидаем
    "Accept-Language": "ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",  # Важный заголовок, указывающий на AJAX-запрос
    "Origin": "https://miet.ru",
    "Referer": "https://miet.ru/schedule/",
    "DNT": "1",
    "Connection": "keep-alive",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}


def get_all_groups():
    """Получает список всех групп с сайта МИЭТ."""
    groups_url = f"{BASE_URL}/groups"
    try:
        response = requests.get(groups_url, headers=HEADERS)
        response.raise_for_status()
        groups_data = response.json()
        return groups_data
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при получении списка групп: {e}")
        if response is not None:
            print(f"Текст ответа сервера: {response.text}")
    except json.JSONDecodeError:
        print("Ошибка декодирования JSON ответа для списка групп.")
    return None


def get_schedule_for_group(group_name):
    """Получает расписание для указанной группы."""
    schedule_url = f"{BASE_URL}/data"

    # Кодируем имя группы для POST-запроса
    # Имя параметра 'group' и его значение в URL-кодировке
    payload = f"group={quote(group_name.encode('utf-8'))}"

    try:
        response = requests.post(schedule_url, data=payload, headers=HEADERS)
        response.raise_for_status()
        schedule_json = response.json()
        return schedule_json  # Возвращаем весь JSON-объект
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при получении расписания для группы {group_name}: {e}")
        if response is not None:
            print(f"Статус код: {response.status_code}")
            print(f"Текст ответа сервера: {response.text}")
    except json.JSONDecodeError:
        print(f"Ошибка декодирования JSON ответа для расписания группы {group_name}.")
        if response is not None:
            print(f"Текст ответа сервера (возможно, не JSON): {response.text}")
    return None


def format_schedule_item(item):
    """Форматирует одну запись расписания для вывода."""
    # Соответствие числового дня недели строковому представлению
    days_map = {
        1: "Понедельник",
        2: "Вторник",
        3: "Среда",
        4: "Четверг",
        5: "Пятница",
        6: "Суббота",
        7: "Воскресенье",
    }
    day_num = item.get("Day")
    day_str = days_map.get(day_num, f"День {day_num}")

    time_info = item.get("Time", {})
    class_info = item.get("Class", {})
    room_info = item.get("Room", {})

    time_str = time_info.get("Time", "N/A")  # "1 пара"
    # Для получения времени HH:MM-HH:MM можно использовать TimeFrom и TimeTo, но это потребует парсинга даты
    # Пока оставим "1 пара"

    subject_full_name = class_info.get(
        "Name", "N/A"
    )  # "Дифференциальные уравнения [Лек]"
    # Извлечем тип занятия из названия, если он там есть
    class_type = ""
    if "[" in subject_full_name and "]" in subject_full_name:
        start_bracket = subject_full_name.rfind("[")
        end_bracket = subject_full_name.rfind("]")
        if start_bracket != -1 and end_bracket != -1 and start_bracket < end_bracket:
            class_type = subject_full_name[start_bracket + 1 : end_bracket]
            subject_name = subject_full_name[:start_bracket].strip()
        else:
            subject_name = subject_full_name
    else:
        subject_name = subject_full_name

    room = room_info.get("Name", "N/A")
    teacher = class_info.get("Teacher", "N/A")
    is_distant = class_info.get("Form", False)  # true если дистанционно
    distant_str = "[ДСТ] " if is_distant else ""

    day_number_val = item.get("DayNumber")
    week_type_str = ""
    # Интерпретация DayNumber (нужно проверить и уточнить):
    # 0 - каждая неделя или 1-я из 4х (числитель)
    # 1 - числитель или 2-я из 4х (знаменатель)
    # 2 - знаменатель или 3-я из 4х (числитель)
    # 3 - "второй знаменатель" или 4-я из 4х (знаменатель)
    # Это предположение, которое нужно будет проверить по реальному расписанию.
    # Простая схема: 0,2 - числитель (или всегда), 1,3 - знаменатель.
    # Более точная, если это 4-недельное расписание:
    if day_number_val == 0:
        week_type_str = "(1-я нед. / числ.)"  # или (каждую неделю)
    elif day_number_val == 1:
        week_type_str = "(2-я нед. / знам.)"
    elif day_number_val == 2:
        week_type_str = "(3-я нед. / числ.)"
    elif day_number_val == 3:
        week_type_str = "(4-я нед. / знам.)"
    else:
        week_type_str = "(неделя ?)"

    # Если на сайте есть информация о текущей неделе (числитель/знаменатель), ее можно использовать для фильтрации
    # Пока выводим все, с пометкой.

    return (
        f"  {time_str}: {distant_str}{subject_name} [{class_type}] - Ауд: {room}, "
        f"Преп: {teacher} {week_type_str}"
    )


def display_schedule(full_schedule_data):
    """Выводит расписание, сгруппированное по дням."""
    schedule_data = full_schedule_data.get("Data")
    if not schedule_data:
        print("Нет данных о занятиях в ответе сервера.")
        return

    semestr = full_schedule_data.get("Semestr", "Неизвестный семестр")
    print(f"\n--- Расписание на {semestr} ---")

    # Группируем по дням недели
    schedule_by_day = {}
    for item in schedule_data:
        day_num = item.get("Day")
        if day_num not in schedule_by_day:
            schedule_by_day[day_num] = []
        schedule_by_day[day_num].append(item)

    # Порядок дней недели для вывода
    days_order_map = {
        1: "Понедельник",
        2: "Вторник",
        3: "Среда",
        4: "Четверг",
        5: "Пятница",
        6: "Суббота",
        7: "Воскресенье",
    }

    for day_code in sorted(schedule_by_day.keys()):  # Сортируем по числовому коду дня
        day_name = days_order_map.get(day_code, f"День {day_code}")
        print(f"\n--- {day_name} ---")

        # Сортируем занятия по коду времени (номеру пары)
        day_items = sorted(
            schedule_by_day[day_code], key=lambda x: x.get("Time", {}).get("Code", 0)
        )
        for item in day_items:
            print(format_schedule_item(item))


if __name__ == "__main__":
    all_groups = get_all_groups()

    if not all_groups:
        print("Не удалось загрузить список групп. Выход.")
    else:
        print("Доступные группы (первые 10 для примера):")
        for i, group_name in enumerate(all_groups):
            if i < 10:
                print(f"- {group_name}")
            else:
                print(f"... и еще {len(all_groups) - 10}")
                break

        my_group = (
            input("Введите название вашей группы (например, ЭКТ-11): ").strip().upper()
        )

        if my_group in all_groups:  # Проверяем, что введенная группа есть в списке
            print(f"\nПолучение расписания для группы: {my_group}...")
            full_schedule = get_schedule_for_group(my_group)  # Теперь это весь JSON
            if full_schedule and "Data" in full_schedule:
                display_schedule(full_schedule)
            else:
                print(
                    f"Не удалось получить или распарсить расписание для группы {my_group}."
                )
        else:
            print(f"Группа '{my_group}' не найдена в списке доступных групп.")
