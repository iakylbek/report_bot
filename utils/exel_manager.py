from openpyxl import load_workbook, Workbook

from config import FILE_PATH, FILE_NAME


class ExelManager():
    _instance = None

    workbook = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ExelManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            try:
                self.workbook = load_workbook(FILE_PATH)
            except:
                self.workbook = Workbook()
                self.workbook.remove(self.workbook.active)

                self._create_sheet(
                    "Cотрудники", ["Telegram ID", "Имя Пользователя"])
                self._create_sheet(
                    "Товары", ["Артикул", "Наименование", "Цена", "Кто отвественный", "Комментарий"])
                self._create_sheet("Остатки", [
                                   "Ответственный", "Артикул", "Товар", "Поступление", "Отгрузка", "Остаток", "Общая стоимость"])
                self._create_sheet(
                    "Операции", ["Дата", "Товар", "Поступление or откгрузка", "Комментарий"])

                self.save_data()

            self._initialized = True

    def _create_sheet(self, name: str, headers):
        self.workbook.create_sheet(title=f"{name}")
        sheet = self.workbook[name]
        for col, header in enumerate(headers, start=1):
            sheet.cell(row=1, column=col, value=header)

    def save_data(self):
        self.workbook.save(FILE_PATH)

    def add_employee(self, telegram_id, name):
        sheet = self.workbook["Cотрудники"]
        next_row = sheet.max_row + 1

        sheet.cell(row=next_row, column=1, value=telegram_id)
        sheet.cell(row=next_row, column=2, value=name)

        self.save_data()

    def add_product(self, article, name, price, responsible, comment):
        sheet = self.workbook["Товары"]
        next_row = sheet.max_row + 1

        sheet.cell(row=next_row, column=1, value=article)
        sheet.cell(row=next_row, column=2, value=name)
        sheet.cell(row=next_row, column=3, value=price)
        sheet.cell(row=next_row, column=4, value=responsible)
        sheet.cell(row=next_row, column=5, value=comment)

        self.save_data()
