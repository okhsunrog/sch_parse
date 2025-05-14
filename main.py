# main.py (или твой основной скрипт)
from typing import Any, Dict, List, Optional

from miet_schedule_api import (  # Импортируем класс и функции
    MietScheduleClient, MietScheduleError, display_formatted_schedule,
    format_schedule_item_info)


def find_teacher_schedule(teacher_name_part: str):
    """
    Находит и выводит расписание для указанного преподавателя по всем группам.
    """
    client = MietScheduleClient()
    print(f"Поиск расписания для преподавателя, содержащего: '{teacher_name_part}'")

    all_groups = client.get_all_groups()
    if not all_groups:
        print("Не удалось получить список групп.")
        return

    teacher_schedule_items: List[Dict[str, Any]] = []
    processed_groups = 0
    total_groups = len(all_groups)

    print(f"Всего групп для обработки: {total_groups}")

    for i, group_name in enumerate(all_groups):
        # Для примера можно ограничить количество групп для теста
        # if i >= 10: # Убери или настрой для полного сканирования
        #     print("Достигнут лимит тестовых групп.")
        #     break

        print(f"Обработка группы {i+1}/{total_groups}: {group_name}...")
        group_schedule_data = client.get_schedule_for_group(group_name)

        if group_schedule_data and "Data" in group_schedule_data:
            for item in group_schedule_data["Data"]:
                class_info = item.get("Class", {})
                teacher_short = class_info.get("Teacher", "")
                teacher_full = class_info.get("TeacherFull", "")

                # Проверяем и краткое, и полное имя преподавателя
                if (
                    teacher_name_part.lower() in teacher_short.lower()
                    or teacher_name_part.lower() in teacher_full.lower()
                ):
                    # Добавляем информацию о группе в элемент расписания для удобства
                    item_copy = (
                        item.copy()
                    )  # Копируем, чтобы не изменять исходные данные
                    item_copy["Group"] = {
                        "Name": group_name
                    }  # Или взять из item.get("Group", {}).get("Name") если есть
                    teacher_schedule_items.append(item_copy)
        processed_groups += 1

    if not teacher_schedule_items:
        print(f"Занятия для преподавателя '{teacher_name_part}' не найдены.")
        return

    print(f"\n--- Найдено расписание для преподавателя '{teacher_name_part}' ---")

    # Можно отсортировать по дню, потом по номеру недели, потом по времени
    # Day (1-6), DayNumber (0-3), Time.Code (1-8)
    teacher_schedule_items_sorted = sorted(
        teacher_schedule_items,
        key=lambda x: (
            x.get("Day", 0),
            x.get("DayNumber", 0),
            x.get("Time", {}).get("Code", 0),
        ),
    )

    # Отображение (можно создать свою функцию для этого или адаптировать display_formatted_schedule)
    # Для простоты, сгруппируем как в display_formatted_schedule
    # Семестр может быть разным, если преподаватель ведет в разных семестрах (маловероятно для одного запроса, но...)
    # Возьмем семестр из первого найденного расписания, если есть
    example_semestr = "не определен"
    if teacher_schedule_items_sorted:
        # Пытаемся получить семестр из данных группы, если он там есть
        first_item_group_name = (
            teacher_schedule_items_sorted[0].get("Group", {}).get("Name")
        )
        if first_item_group_name:
            first_group_data = client.get_schedule_for_group(
                first_item_group_name
            )  # Повторный запрос, не оптимально
            if first_group_data and "Semestr" in first_group_data:
                example_semestr = first_group_data["Semestr"]

    display_formatted_schedule(teacher_schedule_items_sorted, semestr=example_semestr)


if __name__ == "__main__":
    client = MietScheduleClient()

    # --- Сценарий 1: Расписание своей группы ---
    # all_groups_list = client.get_all_groups()
    # if not all_groups_list:
    #     print("Выход.")
    # else:
    #     print("\nДоступные группы (первые 5 для примера):")
    #     for i, group_name_from_list in enumerate(all_groups_list):
    #         if i < 5:
    #             print(f"- {group_name_from_list}")
    #         else:
    #             print(f"... и еще {len(all_groups_list) - 5}")
    #             break
    #
    #     my_group_input = input("Введите название вашей группы: ").strip()
    #
    #     found_group_name = None
    #     for g_name in all_groups_list:
    #         if g_name.upper() == my_group_input.upper():
    #             found_group_name = g_name
    #             break
    #
    #     if found_group_name:
    #         print(f"\nПолучение расписания для группы: {found_group_name}...")
    #         full_schedule = client.get_schedule_for_group(found_group_name)
    #
    #         if full_schedule and "Data" in full_schedule:
    #             current_week_num = client.get_current_week_day_number()
    #             current_week_text = client.get_week_text_by_day_number(current_week_num)
    #             print(f"(Сейчас: {current_week_text})")
    #
    #             filter_choice = (
    #                 input(
    #                     "Показать расписание: 1-На текущую неделю, 2-На все недели [1]: "
    #                 ).strip()
    #                 or "1"
    #             )
    #
    #             schedule_data_to_display = full_schedule["Data"]
    #             display_week_text_header = None
    #
    #             if filter_choice == "1":
    #                 schedule_data_to_display = [
    #                     item
    #                     for item in full_schedule["Data"]
    #                     if item.get("DayNumber") == current_week_num
    #                 ]
    #                 display_week_text_header = current_week_text
    #             else:  # Показать все
    #                 display_week_text_header = "Все недели"
    #
    #             display_formatted_schedule(
    #                 schedule_data_to_display,
    #                 semestr=full_schedule.get("Semestr", "N/A"),
    #                 current_week_text=display_week_text_header,
    #             )
    #         else:
    #             print(
    #                 f"Не удалось получить или распарсить расписание для группы {found_group_name}."
    #             )
    #     else:
    #         print(f"Группа '{my_group_input}' не найдена.")

    # --- Сценарий 2: Расписание преподавателя ---
    print("\n" + "=" * 30)
    teacher_query = input(
        "Введите фамилию или часть ФИО преподавателя для поиска: "
    ).strip()
    if teacher_query:
        find_teacher_schedule(teacher_query)
    else:
        print("Имя преподавателя не введено.")
