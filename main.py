import flet as ft
import sqlite3
import threading
from datetime import datetime

# --- Database Setup ---
class Database:
    def __init__(self):
        self.conn = sqlite3.connect("salary_app.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
        self.migrate_db()

    def create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS workers (
                id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, age TEXT, number TEXT, address TEXT,
                status TEXT, salary_type TEXT, base_salary REAL, custom_id INTEGER, factory_location TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT, worker_id INTEGER, date TEXT, amount_earned REAL, status TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS advances (
                id INTEGER PRIMARY KEY AUTOINCREMENT, worker_id INTEGER, date TEXT, amount REAL, reason TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT, period_start TEXT, period_end TEXT, worker_name TEXT,
                salary_type TEXT, total_paid REAL, date_saved TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS recycle_bin (
                trash_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, age TEXT, number TEXT, address TEXT,
                status TEXT, salary_type TEXT, base_salary REAL, deleted_date TEXT, custom_id INTEGER, factory_location TEXT
            )
        """)
        self.cursor.execute("CREATE TABLE IF NOT EXISTS custom_deductions (worker_id INTEGER PRIMARY KEY, deduction_amount REAL)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS worker_history (history_id INTEGER PRIMARY KEY AUTOINCREMENT, worker_id INTEGER, change_field TEXT, old_val TEXT, new_val TEXT, date_changed TEXT)")
        
        self.cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
        self.cursor.execute("CREATE TABLE IF NOT EXISTS overtime_history (id INTEGER PRIMARY KEY AUTOINCREMENT, worker_id INTEGER, date TEXT, amount REAL, hours REAL, status TEXT DEFAULT 'Unpaid')")
        
        self.conn.commit()

    def migrate_db(self):
        try: self.cursor.execute("SELECT status FROM attendance LIMIT 1")
        except: 
            self.cursor.execute("ALTER TABLE attendance ADD COLUMN status TEXT")
            self.conn.commit()
        try: self.cursor.execute("SELECT custom_id FROM workers LIMIT 1")
        except: pass
        try: self.cursor.execute("SELECT status FROM overtime_history LIMIT 1")
        except: 
            self.cursor.execute("ALTER TABLE overtime_history ADD COLUMN status TEXT DEFAULT 'Unpaid'")
            self.conn.commit()

    # --- OVERTIME METHODS ---
    def get_setting(self, key, default=""):
        self.cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        res = self.cursor.fetchone()
        return res[0] if res else default

    def set_setting(self, key, value):
        self.cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
        self.conn.commit()

    def add_overtime(self, worker_id, date_str, amount, hours, status='Unpaid'):
        self.cursor.execute("INSERT INTO overtime_history (worker_id, date, amount, hours, status) VALUES (?, ?, ?, ?, ?)", (worker_id, date_str, amount, hours, status))
        self.conn.commit()

    def mark_overtime_paid(self, worker_id, start_date, end_date, actual_paid, total_unpaid):
        self.cursor.execute("UPDATE overtime_history SET status='Paid' WHERE worker_id=? AND date BETWEEN ? AND ? AND status='Unpaid'", (worker_id, start_date, end_date))
        diff = actual_paid - total_unpaid
        if diff != 0:
            pay_date = datetime.now().strftime("%Y-%m-%d")
            self.cursor.execute("INSERT INTO overtime_history (worker_id, date, amount, hours, status) VALUES (?, ?, ?, 0, 'Paid')", (worker_id, pay_date, diff))
        self.conn.commit()

    def mark_overtime_unpaid(self, worker_id, start_date, end_date):
        self.cursor.execute("UPDATE overtime_history SET status='Unpaid' WHERE worker_id=? AND date BETWEEN ? AND ? AND status='Paid' AND hours > 0", (worker_id, start_date, end_date))
        self.cursor.execute("DELETE FROM overtime_history WHERE worker_id=? AND date BETWEEN ? AND ? AND hours = 0 AND status='Paid'", (worker_id, start_date, end_date))
        self.conn.commit()

    def get_overtime_range(self, worker_id, start_date, end_date):
        self.cursor.execute("SELECT SUM(amount) FROM overtime_history WHERE worker_id=? AND date BETWEEN ? AND ?", (worker_id, start_date, end_date))
        res = self.cursor.fetchone()[0]
        return res if res else 0.0

    # --- EXISTING METHODS ---
    def add_worker(self, name, age, number, address, status, s_type, salary, custom_id=None, factory_location=""):
        if custom_id is None:
            self.cursor.execute("SELECT MAX(custom_id) FROM workers WHERE salary_type=?", (s_type,))
            res = self.cursor.fetchone()
            custom_id = (res[0] or 0) + 1
        self.cursor.execute("INSERT INTO workers (name, age, number, address, status, salary_type, base_salary, custom_id, factory_location) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (name, age, number, address, status, s_type, salary, custom_id, factory_location))
        self.conn.commit()

    def get_workers(self, salary_type=None):
        if salary_type: self.cursor.execute("SELECT * FROM workers WHERE salary_type = ?", (salary_type,))
        else: self.cursor.execute("SELECT * FROM workers")
        return self.cursor.fetchall()
    
    def get_distinct_status(self):
        self.cursor.execute("SELECT DISTINCT status FROM workers WHERE status IS NOT NULL AND status != '' ORDER BY status")
        return [row[0] for row in self.cursor.fetchall()]

    def get_distinct_factory(self):
        self.cursor.execute("SELECT DISTINCT factory_location FROM workers WHERE factory_location IS NOT NULL AND factory_location != '' ORDER BY factory_location")
        return [row[0] for row in self.cursor.fetchall()]

    def update_worker(self, w_id, name, age, number, address, status, s_type, salary, custom_id, factory_location):
        self.cursor.execute("UPDATE workers SET name=?, age=?, number=?, address=?, status=?, salary_type=?, base_salary=?, custom_id=?, factory_location=? WHERE id=?", (name, age, number, address, status, s_type, salary, custom_id, factory_location, w_id))
        self.conn.commit()

    def get_worker_history(self, worker_id, field):
        self.cursor.execute("SELECT history_id, date_changed, old_val, new_val FROM worker_history WHERE worker_id=? AND change_field=? ORDER BY history_id DESC", (worker_id, field))
        return self.cursor.fetchall()
        
    def delete_worker_history(self, history_id):
        self.cursor.execute("DELETE FROM worker_history WHERE history_id=?", (history_id,))
        self.conn.commit()
    
    def soft_delete_worker(self, w_id):
        self.cursor.execute("SELECT * FROM workers WHERE id=?", (w_id,))
        w = self.cursor.fetchone()
        if w:
            del_date = datetime.now().strftime("%Y-%m-%d %H:%M")
            self.cursor.execute("INSERT INTO recycle_bin (name, age, number, address, status, salary_type, base_salary, deleted_date, custom_id, factory_location) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (w[1], w[2], w[3], w[4], w[5], w[6], w[7], del_date, w[8], w[9]))
            self.conn.commit()
            self.delete_worker_hard(w_id)

    def get_trash_items(self):
        self.cursor.execute("SELECT * FROM recycle_bin ORDER BY trash_id DESC")
        return self.cursor.fetchall()

    def restore_worker(self, trash_id):
        self.cursor.execute("SELECT * FROM recycle_bin WHERE trash_id=?", (trash_id,))
        t = self.cursor.fetchone()
        if t:
            self.add_worker(t[1], t[2], t[3], t[4], t[5], t[6], t[7], t[9], t[10])
            self.permanent_delete_trash(trash_id)

    def permanent_delete_trash(self, trash_id):
        self.cursor.execute("DELETE FROM recycle_bin WHERE trash_id=?", (trash_id,))
        self.conn.commit()

    def empty_trash(self):
        self.cursor.execute("DELETE FROM recycle_bin")
        self.conn.commit()

    def delete_worker_hard(self, w_id):
        self.cursor.execute("DELETE FROM workers WHERE id=?", (w_id,))
        self.cursor.execute("DELETE FROM attendance WHERE worker_id=?", (w_id,))
        self.cursor.execute("DELETE FROM advances WHERE worker_id=?", (w_id,))
        self.cursor.execute("DELETE FROM custom_deductions WHERE worker_id=?", (w_id,))
        self.cursor.execute("DELETE FROM worker_history WHERE worker_id=?", (w_id,))
        self.cursor.execute("DELETE FROM overtime_history WHERE worker_id=?", (w_id,))
        self.conn.commit()

    def set_custom_deduction(self, worker_id, amount):
        self.cursor.execute("INSERT OR REPLACE INTO custom_deductions (worker_id, deduction_amount) VALUES (?, ?)", (worker_id, amount))
        self.conn.commit()

    def get_custom_deduction(self, worker_id):
        self.cursor.execute("SELECT deduction_amount FROM custom_deductions WHERE worker_id=?", (worker_id,))
        res = self.cursor.fetchone()
        return res[0] if res else None

    def add_advance(self, worker_id, amount, reason, date_str):
        self.cursor.execute("INSERT INTO advances (worker_id, date, amount, reason) VALUES (?, ?, ?, ?)", (worker_id, date_str, amount, reason))
        self.conn.commit()

    def get_worker_advances(self, worker_id, start_date=None, end_date=None):
        if start_date and end_date:
            self.cursor.execute("SELECT SUM(t1.amount) FROM advances t1 LEFT JOIN attendance t2 ON t1.worker_id = t2.worker_id AND t1.date = t2.date WHERE t1.worker_id = ? AND t1.date BETWEEN ? AND ? AND (t2.status IS NULL OR t2.status != 'Absent')", (worker_id, start_date, end_date))
        else:
            self.cursor.execute("SELECT SUM(t1.amount) FROM advances t1 LEFT JOIN attendance t2 ON t1.worker_id = t2.worker_id AND t1.date = t2.date WHERE t1.worker_id = ? AND (t2.status IS NULL OR t2.status != 'Absent')", (worker_id,))
        result = self.cursor.fetchone()[0]
        return result if result else 0.0

    def get_all_advances_detailed(self, salary_type_filter=None, filter_month=None):
        query = "SELECT a.date, w.name, w.salary_type, a.amount, a.reason, a.id FROM advances a JOIN w ON a.worker_id = w.id WHERE 1=1"
        params = []
        if salary_type_filter and salary_type_filter != "All":
            query += " AND w.salary_type = ?"
            params.append(salary_type_filter)
        if filter_month:
            query += " AND a.date LIKE ?"
            params.append(f"{filter_month}%")
        query += " ORDER BY a.date DESC"
        self.cursor.execute(query, tuple(params))
        return self.cursor.fetchall()

    def delete_advance(self, adv_id):
        self.cursor.execute("DELETE FROM advances WHERE id=?", (adv_id,))
        self.conn.commit()

    def set_attendance(self, worker_id, date, amount, status):
        self.cursor.execute("SELECT id FROM attendance WHERE worker_id=? AND date=?", (worker_id, date))
        data = self.cursor.fetchone()
        if data: self.cursor.execute("UPDATE attendance SET amount_earned=?, status=? WHERE id=?", (amount, status, data[0]))
        else: self.cursor.execute("INSERT INTO attendance (worker_id, date, amount_earned, status) VALUES (?, ?, ?, ?)", (worker_id, date, amount, status))
        self.conn.commit()

    def get_attendance_entry(self, worker_id, date):
        self.cursor.execute("SELECT amount_earned, status FROM attendance WHERE worker_id=? AND date=?", (worker_id, date))
        return self.cursor.fetchone() 

    def save_record(self, start_date, end_date, name, s_type, total):
        save_date = datetime.now().strftime("%Y-%m-%d")
        self.cursor.execute("SELECT id FROM records WHERE period_start=? AND period_end=? AND worker_name=?", (start_date, end_date, name))
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO records (period_start, period_end, worker_name, salary_type, total_paid, date_saved) VALUES (?, ?, ?, ?, ?, ?)", (start_date, end_date, name, s_type, total, save_date))
            self.conn.commit()

    def is_period_paid(self, name, start_date, end_date):
        self.cursor.execute("SELECT id FROM records WHERE period_start=? AND period_end=? AND worker_name=?", (start_date, end_date, name))
        return self.cursor.fetchone() is not None

    def delete_period_record(self, start_date, end_date, name):
        self.cursor.execute("DELETE FROM records WHERE period_start=? AND period_end=? AND worker_name=?", (start_date, end_date, name))
        self.conn.commit()

    def delete_record(self, record_id):
        self.cursor.execute("DELETE FROM records WHERE id=?", (record_id,))
        self.conn.commit()

    def get_records(self, filter_month=None, salary_type=None):
        query = "SELECT * FROM records WHERE date_saved LIKE ?"
        params = [f"{filter_month}%"]
        if salary_type and salary_type != "All":
            query += " AND salary_type = ?"
            params.append(salary_type)
        query += " ORDER BY id DESC"
        self.cursor.execute(query, tuple(params))
        return self.cursor.fetchall()

    def get_worker_id_by_name(self, name):
        self.cursor.execute("SELECT id FROM workers WHERE name=?", (name,))
        res = self.cursor.fetchone()
        return res[0] if res else None

    def get_attendance_range(self, worker_id, start_date, end_date):
        self.cursor.execute("SELECT date, amount_earned, status FROM attendance WHERE worker_id=? AND date BETWEEN ? AND ? ORDER BY date", (worker_id, start_date, end_date))
        return self.cursor.fetchall()

    def get_advances_range(self, worker_id, start_date, end_date):
        self.cursor.execute("SELECT date, amount, reason FROM advances WHERE worker_id=? AND date BETWEEN ? AND ? ORDER BY date", (worker_id, start_date, end_date))
        return self.cursor.fetchall()

db = Database()

# --- Main App ---
def main(page: ft.Page):
    page.title = "Worker Salary Manager"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = "#F3F4F6" 
    page.padding = 0  
    page.spacing = 0
    page.window_width = 1300
    page.window_height = 850
    
    # --- REGISTER CUSTOM FONT ---
    page.fonts = {
        "JameelNoori": "Jameel Noori.ttf"
    }
    
    def show_snack(page_obj, text, color):
        snack = ft.SnackBar(ft.Text(text), bgcolor=color)
        if snack not in page_obj.overlay:
            page_obj.overlay.append(snack)
        snack.open = True
        page_obj.update()

    def open_dialog_safe(page_obj, dialog):
        if dialog not in page_obj.overlay:
            page_obj.overlay.append(dialog)
        dialog.open = True
        page_obj.update()

    state = {
        "current_nav_index": 0,
        "att_view_date": datetime.now(),
        "weekly_view_date": datetime.now(),
        "monthly_view_date": datetime.now(),
        "records_view_date": datetime.now(),
        "advances_view_date": datetime.now(),
        "overtime_view_date": datetime.now(),
        "lang": "en" 
    }

    # --- TRANSLATION DICTIONARY FOR MAIN MENU ---
    trans = {
        "Workers": {"en": "Workers", "ur": "ورکرز"},
        "Attendance": {"en": "Attendance", "ur": "حاضری"},
        "Overtime": {"en": "Overtime", "ur": "اوور ٹائم"},
        "Weekly": {"en": "Weekly", "ur": "ہفتہ وار"},
        "Monthly": {"en": "Monthly", "ur": "ماہانہ"},
        "Advances": {"en": "Advances", "ur": "ایڈوانس"},
        "Records": {"en": "Records", "ur": "ریکارڈز"},
        "Settings": {"en": "Settings", "ur": "ترتیبات"},
        "FactoryManager": {"en": "FactoryManager", "ur": "فیکٹری مینیجر"}
    }

    def _(key):
        return trans.get(key, {}).get(state["lang"], key)
        
    def get_font():
        return "JameelNoori" if state["lang"] == "ur" else None

    from workers_tab import get_workers_view
    from attendance_tab import get_attendance_view
    from overtime_tab import get_overtime_view
    from weekly_tab import get_weekly_view
    from monthly_tab import get_monthly_view
    from advances_tab import get_advances_view
    from records_tab import get_records_view
    from settings_tab import get_settings_view

    def reload_weekly_cb(): load_weekly_tab()
    def reload_monthly_cb(): load_monthly_tab()

    workers_view, load_workers_ui = get_workers_view(page, db, show_snack, open_dialog_safe, reload_weekly_cb, reload_monthly_cb)
    attendance_view, load_attendance_ui = get_attendance_view(page, db, state)
    overtime_view, load_overtime_ui = get_overtime_view(page, db, state, show_snack, open_dialog_safe)
    weekly_container, load_weekly_tab = get_weekly_view(page, db, state, show_snack)
    monthly_container, load_monthly_tab = get_monthly_view(page, db, state, show_snack, open_dialog_safe)
    advances_view, load_advances_ui = get_advances_view(page, db, state, show_snack, reload_weekly_cb, reload_monthly_cb)
    records_view, load_records_ui = get_records_view(page, db, state, show_snack, open_dialog_safe, reload_weekly_cb, reload_monthly_cb)
    settings_view, load_general_settings = get_settings_view(page, db, show_snack)

    views_map = {
        0: workers_view,
        1: attendance_view,
        2: overtime_view,
        3: weekly_container,
        4: monthly_container,
        5: advances_view,
        6: records_view,
        7: settings_view
    }

    for i in range(8):
        views_map[i].visible = True 

    main_content_area = ft.Container(content=workers_view, expand=True, padding=20)

    # --- SIDEBAR NAVIGATION ---
    nav_keys = [
        ("Workers", ft.Icons.PEOPLE), 
        ("Attendance", ft.Icons.HOW_TO_REG), 
        ("Overtime", ft.Icons.MORE_TIME), 
        ("Weekly", ft.Icons.VIEW_WEEK), 
        ("Monthly", ft.Icons.CALENDAR_MONTH), 
        ("Advances", ft.Icons.ACCOUNT_BALANCE_WALLET), 
        ("Records", ft.Icons.RECEIPT_LONG),
        ("Settings", ft.Icons.SETTINGS)
    ]

    sidebar_menu = ft.Column(spacing=4, expand=True)

    def create_sidebar_item(key, icon, index):
        is_active = state["current_nav_index"] == index
        bg_color = "#F3F4F6" if is_active else "transparent"
        text_color = "#0284C7" if is_active else "#6B7280"
        font_weight = "bold" if is_active else "w500"
        
        accent_bar = ft.Container(
            width=4, 
            height=24, 
            bgcolor="#0284C7" if is_active else "transparent", 
            border_radius=ft.border_radius.all(4)
        )

        return ft.Container(
            content=ft.Row([
                accent_bar,
                ft.Icon(icon, size=20, color=text_color), 
                ft.Text(_(key), weight=font_weight, size=14, color=text_color, font_family=get_font())
            ], spacing=12),
            padding=ft.Padding.symmetric(horizontal=12, vertical=12),
            bgcolor=bg_color, 
            border_radius=8, 
            ink=True,
            on_click=lambda e, i=index: switch_view(i)
        )

    def render_sidebar():
        sidebar_menu.controls.clear()
        for idx, (key, icn) in enumerate(nav_keys):
            sidebar_menu.controls.append(create_sidebar_item(key, icn, idx))
        page.update()

    def switch_view(index):
        state["current_nav_index"] = index
        render_sidebar()

        main_content_area.content = views_map.get(index)
        
        if index == 0: load_workers_ui()
        elif index == 1: load_attendance_ui()
        elif index == 2: load_overtime_ui()
        elif index == 3: load_weekly_tab()
        elif index == 4: load_monthly_tab()
        elif index == 5: load_advances_ui()
        elif index == 6: load_records_ui()
        elif index == 7: load_general_settings()
        
        page.update()

    # --- SIDEBAR HEADER / PROFILE ---
    app_title = ft.Text(_("FactoryManager"), weight="bold", size=20, color="#111827", font_family=get_font())
    
    profile_section = ft.Container(
        content=ft.Row([
            ft.CircleAvatar(
                content=ft.Icon(ft.Icons.PERSON, color="#0284C7"), 
                bgcolor="#E0F2FE", 
                radius=20
            ),
            ft.Column([
                ft.Text("Hello 👋", size=11, color="#6B7280"),
                ft.Text("Administrator", weight="bold", size=14, color="#111827")
            ], spacing=2)
        ], alignment=ft.MainAxisAlignment.START),
        padding=ft.Padding.only(top=10, bottom=20, left=10)
    )

    # --- SIDEBAR FOOTER (LANG TOGGLE) ---
    lang_btn = ft.TextButton(
        content=ft.Row([
            ft.Icon(ft.Icons.LANGUAGE, size=16, color="#6B7280"),
            ft.Text("اردو", font_family="JameelNoori", color="#6B7280", weight="bold")
        ]), 
        on_click=lambda e: toggle_language(e)
    )

    def toggle_language(e):
        state["lang"] = "ur" if state["lang"] == "en" else "en"
        
        lang_btn.content.controls[1].value = "English" if state["lang"] == "ur" else "اردو"
        lang_btn.content.controls[1].font_family = get_font()
        
        app_title.value = _("FactoryManager")
        app_title.font_family = get_font()
        render_sidebar()
        
        switch_view(state["current_nav_index"])

    sidebar_container = ft.Container(
        content=ft.Column([
            ft.Container(content=app_title, padding=ft.Padding.only(left=10, top=10, bottom=10)),
            profile_section,
            ft.Container(content=ft.Text("MAIN MENU", size=11, weight="bold", color="#9CA3AF"), padding=ft.Padding.only(left=15, bottom=5)),
            sidebar_menu,
            ft.Divider(height=1, color="#E5E7EB"),
            ft.Row([lang_btn], alignment=ft.MainAxisAlignment.CENTER)
        ]),
        width=260,
        bgcolor="#FFFFFF",
        border=ft.border.only(right=ft.border.BorderSide(1, "#E5E7EB")),
        padding=ft.Padding.symmetric(vertical=15, horizontal=15),
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=5, color="#0D000000", offset=ft.Offset(2, 0))
    )

    render_sidebar()

    page.add(
        ft.Row([
            sidebar_container,
            main_content_area
        ], expand=True, spacing=0)
    )
    
    load_workers_ui()

if __name__ == "__main__":
    ft.run(main, assets_dir="assets")