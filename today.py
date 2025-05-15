# get_today_schedule.py
from datetime import datetime
from miet_schedule_api import (
    MietScheduleClient,
    display_formatted_schedule,
    # MietScheduleClient also has static methods for week/day text,
    # but display_formatted_schedule handles most of this.
)

TARGET_GROUP_NAME = "ИВТ-13"


def main():
    client = MietScheduleClient()

    print(f"Получение расписания для группы: {TARGET_GROUP_NAME}")
    full_schedule_data = client.get_schedule_for_group(TARGET_GROUP_NAME)

    if not full_schedule_data:
        print(
            f"Не удалось получить расписание для группы {TARGET_GROUP_NAME}. "
            "Проверьте имя группы или доступность API."
        )
        return

    all_lessons_for_group = full_schedule_data.get("Data", [])
    semestr_name = full_schedule_data.get("Semestr", "Текущий семестр")

    if not all_lessons_for_group:
        print(
            f"Нет данных о расписании для группы {TARGET_GROUP_NAME} в семестре {semestr_name}."
        )
        return

    # Определяем сегодняшний день и номер недели по API
    today_date = datetime.now()
    # API нумерация дней: 1 (Пн) - 7 (Вс)
    # Python datetime.weekday(): 0 (Пн) - 6 (Вс)
    today_api_day_code = today_date.weekday() + 1
    current_week_number = MietScheduleClient.get_current_week_day_number(today_date)
    current_week_text = MietScheduleClient.get_week_text_by_day_number(
        current_week_number
    )

    # Фильтруем занятия на сегодня
    todays_lessons = []
    for lesson in all_lessons_for_group:
        # "Day" - это код дня недели (1-7)
        # "DayNumber" - это номер недели (0-3)
        if (
            lesson.get("Day") == today_api_day_code
            and lesson.get("DayNumber") == current_week_number
        ):
            todays_lessons.append(lesson)

    today_day_string = MietScheduleClient.get_day_string_by_day_code(today_api_day_code)
    print(f"\nРасписание для группы {TARGET_GROUP_NAME} на сегодня:")
    print(f"Дата: {today_date.strftime('%Y-%m-%d')}, {today_day_string}")
    # display_formatted_schedule ожидает полный семестр и текущую неделю для контекста
    # Она сама отфильтрует по дням, но мы уже передаем отфильтрованные данные
    # Это нормально, она просто выведет один день.
    display_formatted_schedule(todays_lessons, semestr_name, current_week_text)

    if not todays_lessons:
        print(
            f"(Занятий на сегодня ({current_week_text}) для группы {TARGET_GROUP_NAME} не найдено)"
        )


if __name__ == "__main__":
    main()
