from utils.exel_manager import ExelManager

em = ExelManager()
em.add_employee("1234567", "Ысаков Акылбек")
em.add_employee("2131231", "James Smit")

em.save_data()
