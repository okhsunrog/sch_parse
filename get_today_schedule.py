# get_today_schedule.py
from datetime import datetime
from miet_schedule_api import (
    MietScheduleClient,
    display_formatted_schedule,  # Эта функция теперь использует _default_format_schedule_item
)
from typing import Dict, Any  # Для аннотаций типов

# Имя группы, для которой нужно получить расписание
TARGET_GROUP_NAME = "ИВТ-13"  # Можете изменить на любую другую группу


def main():
    client = MietScheduleClient()

    print(f"Получение расписания для группы: {TARGET_GROUP_NAME}")
    full_schedule_data: Dict[str, Any] | None = client.get_schedule_for_group(
        TARGET_GROUP_NAME
    )

    if not full_schedule_data:
        print(
            f"Не удалось получить расписание для группы {TARGET_GROUP_NAME}. "
            "Проверьте имя группы или доступность API."
        )
        return

    all_lessons_for_group: list[Dict[str, Any]] = full_schedule_data.get("Data", [])
    semestr_name: str = full_schedule_data.get("Semestr", "Текущий семестр")

    if not all_lessons_for_group:
        print(
            f"Нет данных о расписании для группы {TARGET_GROUP_NAME} в семестре {semestr_name}."
        )
        return

    # Определяем сегодняшний день и номер недели
    today_date = datetime.now()
    # API нумерация дней: 1 (Пн) - 7 (Вс)
    # Python datetime.weekday(): 0 (Пн) - 6 (Вс)
    today_api_day_code = today_date.weekday() + 1
    current_week_number = MietScheduleClient.get_current_week_day_number(today_date)
    current_week_text = MietScheduleClient.get_week_text_by_day_number(
        current_week_number
    )

    # Фильтруем занятия на сегодня (правильный день и правильная неделя)
    todays_lessons: list[Dict[str, Any]] = []
    for lesson in all_lessons_for_group:
        # "Day" - это код дня недели (1-7) из API
        # "DayNumber" - это номер недели (0-3) из API
        if (
            lesson.get("Day") == today_api_day_code
            and lesson.get("DayNumber") == current_week_number
        ):
            todays_lessons.append(lesson)

    today_day_string = MietScheduleClient.get_day_string_by_day_code(today_api_day_code)

    print(f"\nРасписание для группы {TARGET_GROUP_NAME} на сегодня:")
    print(f"Дата: {today_date.strftime('%Y-%m-%d')}, {today_day_string}")

    if not todays_lessons:
        print(
            f"(Занятий на сегодня ({current_week_text}) для группы {TARGET_GROUP_NAME} не найдено)"
        )
    else:
        # display_formatted_schedule теперь по умолчанию использует _default_format_schedule_item,
        # который включает время начала и конца пар.
        # Нам не нужно передавать свой item_formatter, если стандартный нас устраивает.
        display_formatted_schedule(
            todays_lessons,
            semestr_name,
            current_week_text,  # Передаем для отображения информации о текущей неделе
        )


if __name__ == "__main__":
    main()
