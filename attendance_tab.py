import flet as ft
from datetime import datetime, timedelta

def get_attendance_view(page: ft.Page, db, state):
    COLOR_TEXT_MAIN = "#111827"
    COLOR_TEXT_SUB = "#4B5563"
    COLOR_BORDER = "#E5E7EB"
    COLOR_BG_LIGHT = "#F3F4F6"
    COLOR_PRIMARY = "#2D5B7A"

    def local_show_snack(text, color):
        snack = ft.SnackBar(ft.Text(text), bgcolor=color)
        page.overlay.append(snack)
        snack.open = True
        page.update()

    # --- TIME FORMATTERS (AM/PM) ---
    def format_am_pm(time_str):
        if not time_str or time_str in ["--:--", "--"]:
            return ""
        time_str = time_str.strip().upper()
        try:
            if "AM" in time_str or "PM" in time_str:
                return datetime.strptime(time_str, "%I:%M %p").strftime("%I:%M %p")
            return datetime.strptime(time_str, "%H:%M").strftime("%I:%M %p")
        except Exception:
            return time_str

    def parse_to_24h(time_str):
        if not time_str or time_str in ["--:--", "--"]:
            return ""
        time_str = time_str.strip().upper()
        try:
            if "AM" in time_str or "PM" in time_str:
                return datetime.strptime(time_str, "%I:%M %p").strftime("%H:%M")
            return datetime.strptime(time_str, "%H:%M").strftime("%H:%M")
        except Exception:
            return time_str

    # --- DATABASE MIGRATION ---
    try:
        c = db.conn.cursor()
        c.execute("ALTER TABLE attendance ADD COLUMN entry_time TEXT")
        c.execute("ALTER TABLE attendance ADD COLUMN closing_time TEXT")
        db.conn.commit()
    except Exception:
        pass

    try:
        c = db.conn.cursor()
        c.execute("ALTER TABLE attendance ADD COLUMN daily_deduction REAL DEFAULT 0")
        db.conn.commit()
    except Exception:
        pass

    att_grid = ft.ListView(spacing=0, expand=True)
    date_label = ft.Text("", size=16, weight="bold")
    stats_container = ft.Container()
    
    filter_state = {"mode": "All"}

    if "att_view_date" not in state:
        state["att_view_date"] = datetime.now()

    safe_first = datetime(2000, 1, 1)
    safe_last = datetime(2035, 12, 31)

    def on_date_picked(e):
        if e.control.value:
            state["att_view_date"] = e.control.value
            page.run_thread(load_attendance_ui)

    date_picker = ft.DatePicker(
        first_date=safe_first, 
        last_date=safe_last, 
        on_change=on_date_picked
    )

    def open_date_picker(e):
        if date_picker not in page.overlay:
            page.overlay.append(date_picker)
        date_picker.value = state["att_view_date"]
        date_picker.open = True
        page.update()

    date_clickable = ft.Container(
        content=date_label,
        on_click=open_date_picker,
        ink=True, 
        padding=ft.padding.symmetric(horizontal=10, vertical=5), 
        border_radius=5, 
        tooltip="Click to pick a specific date"
    )

    def change_date(days=0):
        if days == "today":
            state["att_view_date"] = datetime.now()
        else:
            state["att_view_date"] += timedelta(days=days)
        page.run_thread(load_attendance_ui)

    search_input = ft.TextField(
        label="Search Name, ID, or Factory...",
        width=250, 
        border_radius=8, 
        content_padding=12, 
        border_color="#D1D5DB", 
        bgcolor="#F9FAFB", 
        height=40, 
        prefix_icon=ft.Icons.SEARCH,
        on_change=lambda e: page.run_thread(load_attendance_ui)
    )

    def with_opacity(opacity, hex_color):
        alpha = hex(int(opacity * 255))[2:].zfill(2).upper()
        base_color = hex_color.lstrip('#')
        if len(base_color) == 8: base_color = base_color[2:]
        return f"#{alpha}{base_color}"
        
    def create_stat_card(title, value, icon, icon_color, on_click_action, is_active):
        bg_color = with_opacity(0.08, icon_color) if is_active else "white"
        border_color = icon_color if is_active else COLOR_BORDER
        border_width = 2 if is_active else 1
        return ft.Container(
            content=ft.Row([
                ft.Container(content=ft.Icon(icon, size=24, color=icon_color), bgcolor=with_opacity(0.15, icon_color), padding=10, border_radius=50),
                ft.Column([
                    ft.Text(title, size=12, color="grey700", weight="w600"), 
                    ft.Text(str(value), size=18, weight="bold", color=icon_color)
                ], spacing=0)
            ]),
            expand=True, 
            bgcolor=bg_color, 
            padding=15, 
            border_radius=8, 
            border=ft.border.all(border_width, border_color),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=2, color="#0A000000", offset=ft.Offset(0, 1)),
            on_click=on_click_action, 
            ink=True
        )

    def set_filter(mode):
        filter_state["mode"] = mode
        page.run_thread(load_attendance_ui)

    # --- AUTO DEDUCTION CALCULATION ENGINE ---
    def get_auto_deduction(entry_time, closing_time):
        if not entry_time: return 0.0
        
        f_entry_str = db.get_setting("factory_entry_time", "08:00 AM")
        f_close_str = db.get_setting("factory_closing_time", "06:00 PM")
        late_after_str = db.get_setting("late_after_time", "08:30 AM")
        early_before_str = db.get_setting("going_before_time", "05:30 PM")
        
        try: pen_amt = float(db.get_setting("penalty_amount", "50"))
        except: pen_amt = 50.0
        
        try: pen_mins = float(db.get_setting("penalty_mins", "30"))
        except: pen_mins = 30.0
        
        def parse_t(t_str):
            try: return datetime.strptime(t_str.strip().upper(), "%I:%M %p")
            except: return datetime.strptime(t_str.strip(), "%H:%M")
            
        late_m = 0
        early_m = 0
        
        try:
            t_entry = parse_t(entry_time)
            f_entry = parse_t(f_entry_str)
            late_after = parse_t(late_after_str)
            
            if t_entry.time() > late_after.time():
                dt_entry = datetime.combine(datetime.min, t_entry.time())
                df_entry = datetime.combine(datetime.min, f_entry.time())
                diff = (dt_entry - df_entry).total_seconds() / 60.0
                if diff > 0: late_m = diff
        except: pass
        
        if closing_time:
            try:
                t_close = parse_t(closing_time)
                f_close = parse_t(f_close_str)
                early_before = parse_t(early_before_str)
                
                if t_close.time() < early_before.time():
                    dt_close = datetime.combine(datetime.min, t_close.time())
                    df_close = datetime.combine(datetime.min, f_close.time())
                    diff = (df_close - dt_close).total_seconds() / 60.0
                    if diff > 0: early_m = diff
            except: pass
            
        total_m = late_m + early_m
        if pen_mins > 0 and total_m > 0:
            steps = int(total_m / pen_mins)
            return float(steps * pen_amt)
        return 0.0

    # --- DB UPDATES FOR MANUAL EDITS ---
    def save_manual_times(worker_id, base_salary, s_type, entry_time, closing_time, manual_deduction=None):
        date_str = state["att_view_date"].strftime("%Y-%m-%d")
        
        c = db.conn.cursor()
        c.execute("SELECT id FROM attendance WHERE worker_id=? AND date=?", (worker_id, date_str))
        existing = c.fetchone()
        
        if not entry_time and not closing_time:
            status_val = "Absent"
            earned = 0
            deduction = 0.0
        else:
            status_val = "Present"
            # Weekly base_salary is now treated as Daily Salary. Monthly is / 26.
            base_daily = base_salary if s_type == "Weekly" else (base_salary / 26)
            
            if manual_deduction is not None:
                deduction = manual_deduction
            else:
                deduction = get_auto_deduction(entry_time, closing_time)
            
            earned = base_daily - deduction
            if earned < 0: earned = 0
            
        if existing:
            c.execute("UPDATE attendance SET amount_earned=?, status=?, entry_time=?, closing_time=?, daily_deduction=? WHERE id=?", (earned, status_val, entry_time, closing_time, deduction, existing[0]))
        else:
            c.execute("INSERT INTO attendance (worker_id, date, amount_earned, status, entry_time, closing_time, daily_deduction) VALUES (?, ?, ?, ?, ?, ?, ?)", (worker_id, date_str, earned, status_val, entry_time, closing_time, deduction))
        
        db.conn.commit()
        load_attendance_ui()

    def quick_punch_action(worker_id, base_salary, s_type, current_entry, current_closing, action_type):
        now_time_24h = datetime.now().strftime("%H:%M")
        
        new_entry = now_time_24h if action_type == "entry" else current_entry
        new_closing = now_time_24h if action_type == "closing" else current_closing
        
        save_manual_times(worker_id, base_salary, s_type, new_entry, new_closing)
        display_now = datetime.now().strftime("%I:%M %p")
        local_show_snack(f"Marked {action_type} at {display_now}", "green")
        
    # --- TIME EDIT DIALOG ---
    time_edit_dialog = ft.AlertDialog()
    
    def open_time_edit(w_id, w_name, w_base, w_type, current_entry, current_closing):
        entry_input = ft.TextField(label="Entry Time", hint_text="08:30 AM", value=format_am_pm(current_entry), width=150, border_radius=8, prefix_icon=ft.Icons.LOGIN)
        closing_input = ft.TextField(label="Closing Time", hint_text="05:00 PM", value=format_am_pm(current_closing), width=150, border_radius=8, prefix_icon=ft.Icons.LOGOUT)
        
        def save_times_dialog(e):
            time_edit_dialog.open = False
            page.update()
            
            parsed_entry = parse_to_24h(entry_input.value)
            parsed_closing = parse_to_24h(closing_input.value)
            
            page.run_thread(save_manual_times, w_id, w_base, w_type, parsed_entry, parsed_closing)
            local_show_snack("Times updated successfully!", "green")

        time_edit_dialog.title = ft.Text(f"Edit Times: {w_name}", weight="bold")
        time_edit_dialog.content = ft.Container(
            content=ft.Column([
                ft.Text("Enter time (e.g. 08:30 AM). Leave BOTH empty to mark as Absent.", color="grey", size=12),
                ft.Row([entry_input, closing_input], spacing=10)
            ], tight=True),
            padding=10
        )
        time_edit_dialog.actions = [
            ft.TextButton("Cancel", on_click=lambda e: setattr(time_edit_dialog, 'open', False) or page.update()),
            ft.ElevatedButton("Save Times", bgcolor=COLOR_PRIMARY, color="white", on_click=save_times_dialog)
        ]
        
        if time_edit_dialog not in page.overlay:
            page.overlay.append(time_edit_dialog)
            
        time_edit_dialog.open = True
        page.update()

    # --- LATE DEDUCTION SYSTEM DIALOG ---
    def open_pay_deduction_dialog(w_id, w_name, w_base, w_type, entry_t, closing_t):
        date_str = state["att_view_date"].strftime("%Y-%m-%d")
        c = db.conn.cursor()
        c.execute("SELECT daily_deduction FROM attendance WHERE worker_id=? AND date=?", (w_id, date_str))
        res = c.fetchone()
        current_deduction = res[0] if res and res[0] is not None else get_auto_deduction(entry_t, closing_t)
        
        # Weekly base_salary is now treated as Daily Salary. Monthly is / 26.
        base_daily = w_base if w_type == "Weekly" else (w_base / 26)
        
        late_after_in = ft.TextField(label="Late After", value=db.get_setting("late_after_time", "08:30 AM"), width=150, border_radius=8, hint_text="08:30 AM")
        going_before_in = ft.TextField(label="Going Before", value=db.get_setting("going_before_time", "05:30 PM"), width=150, border_radius=8, hint_text="05:30 PM")
        
        pen_amt_in = ft.TextField(label="Penalty Amount (PKR)", value=db.get_setting("penalty_amount", "50"), width=150, border_radius=8)
        pen_mins_in = ft.TextField(label="Per (Mins)", value=db.get_setting("penalty_mins", "30"), width=150, border_radius=8)
        
        info_text = ft.Text("", weight="bold", size=13)
        deduction_input = ft.TextField(label="Deduction Amount (PKR)", value=str(int(current_deduction)), border_color="red", border_radius=8)

        def update_calc(e=None):
            if e is not None:
                db.set_setting("late_after_time", late_after_in.value)
                db.set_setting("going_before_time", going_before_in.value)
                db.set_setting("penalty_amount", pen_amt_in.value)
                db.set_setting("penalty_mins", pen_mins_in.value)
            
            auto_ded = get_auto_deduction(entry_t, closing_t)
            
            late_m = 0
            early_m = 0
            f_entry_str = db.get_setting("factory_entry_time", "08:00 AM")
            f_close_str = db.get_setting("factory_closing_time", "06:00 PM")
            
            def parse_t(t_str):
                try: return datetime.strptime(t_str.strip().upper(), "%I:%M %p")
                except: return datetime.strptime(t_str.strip(), "%H:%M")
                
            if entry_t:
                try:
                    if parse_t(entry_t).time() > parse_t(late_after_in.value).time():
                        late_m = (datetime.combine(datetime.min, parse_t(entry_t).time()) - datetime.combine(datetime.min, parse_t(f_entry_str).time())).total_seconds() / 60.0
                except: pass
            if closing_t:
                try:
                    if parse_t(closing_t).time() < parse_t(going_before_in.value).time():
                        early_m = (datetime.combine(datetime.min, parse_t(f_close_str).time()) - datetime.combine(datetime.min, parse_t(closing_t).time())).total_seconds() / 60.0
                except: pass
            
            msg = []
            if late_m > 0: msg.append(f"Late: {int(late_m)}m")
            if early_m > 0: msg.append(f"Left Early: {int(early_m)}m")
            
            if not msg:
                if not entry_t:
                    info_text.value = "Worker is absent or missing entry time."
                    info_text.color = "grey"
                else:
                    info_text.value = "Worker is on time."
                    info_text.color = "green"
            else:
                info_text.value = " | ".join(msg) + f"  -> Auto Penalty: {int(auto_ded)} PKR"
                info_text.color = "red"
            
            if e is not None: 
                deduction_input.value = str(int(auto_ded))
            
            page.update()

        late_after_in.on_change = update_calc
        going_before_in.on_change = update_calc
        pen_amt_in.on_change = update_calc
        pen_mins_in.on_change = update_calc

        def save_deduction(e):
            try: ded_amt = float(deduction_input.value)
            except: local_show_snack("Invalid deduction amount.", "red"); return
            
            save_manual_times(w_id, w_base, w_type, entry_t, closing_t, manual_deduction=ded_amt)
            
            ded_dlg.open = False
            page.update()
            local_show_snack("Deduction updated successfully!", "green")

        ded_dlg = ft.AlertDialog(
            title=ft.Text(f"Salary Deduction Rules: {w_name}", weight="bold"),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Base Daily Pay: {int(base_daily)} PKR", weight="bold"),
                    ft.Row([
                        ft.Text(f"Entry: {format_am_pm(entry_t) if entry_t else '--'}", color=COLOR_TEXT_SUB),
                        ft.Text(f"Close: {format_am_pm(closing_t) if closing_t else '--'}", color=COLOR_TEXT_SUB)
                    ], spacing=15),
                    ft.Divider(height=10, color="transparent"),
                    ft.Row([late_after_in, going_before_in], spacing=10),
                    ft.Row([pen_amt_in, pen_mins_in], spacing=10),
                    info_text,
                    ft.Divider(height=10, color="transparent"),
                    deduction_input,
                    ft.Text("You can edit the final deduction amount manually.", size=11, color="grey")
                ], tight=True), width=350
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(ded_dlg, 'open', False) or page.update()),
                ft.ElevatedButton("Save Deduction", bgcolor="#EF4444", color="white", on_click=save_deduction)
            ]
        )
        
        page.overlay.append(ded_dlg)
        ded_dlg.open = True
        update_calc()

    # --- PROFESSIONAL UI BADGE GENERATOR ---
    def make_time_badge(text, color_hex, is_absent, on_click_action=None):
        if is_absent:
            content_ui = ft.Text("ABSENT", size=11, weight="bold", color="white", text_align=ft.TextAlign.CENTER)
            bg_color = "#EF4444"
            border_ui = None
        elif text == "--":
            content_ui = ft.Text("--", color="#9CA3AF", weight="bold", size=14, text_align=ft.TextAlign.CENTER)
            bg_color = "transparent"
            border_ui = None
        else:
            content_ui = ft.Row([
                ft.Icon(ft.Icons.ACCESS_TIME, size=14, color=color_hex),
                ft.Text(text, color=color_hex, weight="bold", size=12)
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=4)
            bg_color = f"{color_hex}15"
            border_ui = ft.border.all(1, f"{color_hex}30")

        return ft.Container(
            content=content_ui,
            bgcolor=bg_color, border=border_ui, border_radius=6, width=100, height=28, alignment=ft.Alignment(0, 0),
            ink=True if on_click_action else False,
            on_click=on_click_action,
            tooltip="Click to edit time" if on_click_action else None
        )

    def load_attendance_ui(e=None):
        new_list_controls = []
        
        curr_date = state["att_view_date"]
        date_str = curr_date.strftime("%Y-%m-%d")
        date_label.value = curr_date.strftime("%A, %d %b %Y")
        
        workers = db.get_workers()
        query = search_input.value.lower() if search_input.value else ""

        total_workers = len(workers)
        weekly_count = sum(1 for w in workers if w[6] == "Weekly")
        monthly_count = sum(1 for w in workers if w[6] == "Monthly")

        stats_container.content = ft.Row([
            create_stat_card("Total Attendance", total_workers, ft.Icons.PEOPLE_ALT, "#3B82F6", lambda e: set_filter("All"), filter_state["mode"] == "All"),
            create_stat_card("Weekly Shift", weekly_count, ft.Icons.VIEW_WEEK, "#F59E0B", lambda e: set_filter("Weekly"), filter_state["mode"] == "Weekly"),
            create_stat_card("Monthly Shift", monthly_count, ft.Icons.CALENDAR_MONTH, "#10B981", lambda e: set_filter("Monthly"), filter_state["mode"] == "Monthly")
        ], spacing=15)

        new_list_controls.append(
            ft.Container(
                content=ft.Row([
                    ft.Text("ID", width=60, weight="bold", color=COLOR_TEXT_SUB, size=13),
                    ft.Text("Name", width=160, weight="bold", color=COLOR_TEXT_SUB, size=13),
                    ft.Text("Factory", width=100, weight="bold", color=COLOR_TEXT_SUB, size=13),
                    ft.Text("Entry Time", width=100, weight="bold", color=COLOR_TEXT_SUB, size=13, text_align=ft.TextAlign.CENTER),
                    ft.Text("Closing Time", width=100, weight="bold", color=COLOR_TEXT_SUB, size=13, text_align=ft.TextAlign.CENTER),
                    ft.Text("Today's Pay", width=100, weight="bold", color=COLOR_TEXT_SUB, size=13, text_align=ft.TextAlign.CENTER),
                    ft.Container(expand=True), 
                    ft.Text("Quick Punch", width=110, weight="bold", color=COLOR_TEXT_SUB, size=13, text_align=ft.TextAlign.CENTER),
                ]),
                bgcolor=COLOR_BG_LIGHT, padding=ft.padding.symmetric(vertical=10, horizontal=15), border=ft.border.only(bottom=ft.border.BorderSide(2, COLOR_BORDER))
            )
        )
        
        visible_index = 0
        c = db.conn.cursor() 
        
        for w in workers:
            w_id = w[0]
            w_name = w[1]
            w_type = w[6]
            w_base = w[7]
            w_custom_id = w[8]
            w_factory = w[9] or "N/A"
            
            display_id = f"W-{w_custom_id}" if w_type == "Weekly" else f"M-{w_custom_id}"
            
            if filter_state["mode"] != "All" and w_type != filter_state["mode"]:
                continue
            if query and query not in w_name.lower() and query not in display_id.lower() and query not in w_factory.lower():
                continue
            
            c.execute("SELECT status, entry_time, closing_time, daily_deduction FROM attendance WHERE worker_id=? AND date=?", (w_id, date_str))
            entry = c.fetchone()
            
            status = entry[0] if entry else "Not Marked"
            entry_t = entry[1] if (entry and len(entry) > 1 and entry[1]) else ""
            closing_t = entry[2] if (entry and len(entry) > 2 and entry[2]) else ""
            deduction = entry[3] if (entry and len(entry) > 3 and entry[3] is not None) else 0.0
            
            is_absent_entry = (status == "Absent" and not entry_t)
            is_absent_closing = (status == "Absent" and not closing_t)

            entry_display = format_am_pm(entry_t) if entry_t else "--"
            closing_display = format_am_pm(closing_t) if closing_t else "--"

            entry_ui = make_time_badge(entry_display, "#10B981", is_absent_entry, on_click_action=lambda e, wid=w_id, wn=w_name, wb=w_base, wt=w_type, et=entry_t, ct=closing_t: open_time_edit(wid, wn, wb, wt, et, ct))
            closing_ui = make_time_badge(closing_display, "#F59E0B", is_absent_closing, on_click_action=lambda e, wid=w_id, wn=w_name, wb=w_base, wt=w_type, et=entry_t, ct=closing_t: open_time_edit(wid, wn, wb, wt, et, ct))
            
            # Weekly base_salary is now treated as Daily Salary. Monthly is / 26.
            base_daily = w_base if w_type == "Weekly" else (w_base / 26)
            
            if status == "Present":
                today_pay = base_daily - deduction
            else:
                today_pay = 0.0

            pay_color = "#10B981" if deduction == 0 and status == "Present" else ("#EF4444" if status == "Absent" else "#F59E0B")
            pay_ui = ft.Container(
                content=ft.Row([
                    ft.Text(f"{int(today_pay)} PKR", color=pay_color, weight="bold", size=13),
                    ft.Icon(ft.Icons.EDIT_NOTE, size=14, color=pay_color)
                ], spacing=4, alignment=ft.MainAxisAlignment.CENTER),
                width=100, ink=True, border_radius=6, padding=ft.padding.symmetric(horizontal=4, vertical=4),
                on_click=lambda e, wid=w_id, wn=w_name, wb=w_base, wt=w_type, et=entry_t, ct=closing_t: open_pay_deduction_dialog(wid, wn, wb, wt, et, ct),
                tooltip="Click to manage deductions"
            )

            # Segmented Control for Quick Punch
            mark_in_btn = ft.IconButton(
                icon=ft.Icons.LOGIN, 
                icon_color="#10B981" if not entry_t else "#9CA3AF", 
                icon_size=18, 
                width=35, height=35, 
                disabled=bool(entry_t),
                on_click=lambda e, wid=w_id, wb=w_base, wt=w_type, et=entry_t, ct=closing_t: page.run_thread(quick_punch_action, wid, wb, wt, et, ct, "entry"),
                tooltip="Mark In (Now)"
            )
            
            mark_out_btn = ft.IconButton(
                icon=ft.Icons.LOGOUT, 
                icon_color="#F59E0B" if (entry_t and not closing_t) else "#9CA3AF", 
                icon_size=18, 
                width=35, height=35, 
                disabled=bool(closing_t) or not bool(entry_t),
                on_click=lambda e, wid=w_id, wb=w_base, wt=w_type, et=entry_t, ct=closing_t: page.run_thread(quick_punch_action, wid, wb, wt, et, ct, "closing"),
                tooltip="Mark Out (Now)"
            )
            
            punch_ui = ft.Container(
                content=ft.Row([mark_in_btn, mark_out_btn], spacing=0, alignment=ft.MainAxisAlignment.CENTER),
                width=110, bgcolor="#F3F4F6", border_radius=8, border=ft.border.all(1, COLOR_BORDER), alignment=ft.Alignment(0, 0), padding=2
            )

            def make_hover(idx):
                def hover(e):
                    e.control.bgcolor = "#F1F5F9" if e.data == "true" else ("white" if idx % 2 == 0 else "#FAFAFA")
                    e.control.update() 
                return hover

            new_list_controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(display_id, width=60, weight="w600", color=COLOR_TEXT_MAIN, size=13),
                        ft.Text(w_name, width=160, weight="bold", color=COLOR_TEXT_MAIN, size=15),
                        ft.Text(w_factory, width=100, color=COLOR_TEXT_SUB, size=13),
                        entry_ui,
                        closing_ui,
                        pay_ui,
                        ft.Container(expand=True), 
                        punch_ui
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(vertical=8, horizontal=15), 
                    bgcolor="white" if visible_index % 2 == 0 else "#FAFAFA", 
                    border=ft.border.only(bottom=ft.border.BorderSide(1, COLOR_BORDER)),
                    on_hover=make_hover(visible_index)
                )
            )
            visible_index += 1

        att_grid.controls = new_list_controls
        
        try:
            stats_container.update()
            att_grid.update()
        except Exception:
            pass
        page.update()

    att_view = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Daily Attendance", size=22, weight="bold", color=COLOR_TEXT_MAIN),
                ft.Row([
                    ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, on_click=lambda e: change_date(-1)),
                    date_clickable,
                    ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, on_click=lambda e: change_date(1)),
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([
                    search_input, 
                    ft.FilledButton("Today", icon=ft.Icons.TODAY, on_click=lambda e: change_date("today"), bgcolor="#2D5B7A")
                ], spacing=10)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=5, color="transparent"),
            stats_container, ft.Divider(height=5, color="transparent"),
            ft.Container(
                content=att_grid, expand=True, bgcolor="white", border_radius=8, border=ft.border.all(1, COLOR_BORDER), shadow=ft.BoxShadow(spread_radius=1, blur_radius=2, color="#0D000000", offset=ft.Offset(0, 1)), clip_behavior=ft.ClipBehavior.HARD_EDGE
            )
        ], expand=True),
        visible=False
    )

    return att_view, load_attendance_ui