import flet as ft
from datetime import datetime, timedelta

def get_weekly_view(page: ft.Page, db, state, show_snack):
    COLOR_TEXT_MAIN = "#111827"
    COLOR_TEXT_SUB = "#4B5563"
    COLOR_BORDER = "#E5E7EB"
    COLOR_BG_LIGHT = "#F3F4F6"
    COLOR_PRIMARY = "#2D5B7A"
    
    weekly_grid = ft.ListView(spacing=0, expand=True)
    week_label = ft.Text("", size=16, weight="bold")
    
    if "week_view_mode" not in state:
        state["week_view_mode"] = "Week"
        state["weekly_view_date"] = datetime.now()

    def get_week_range(ref_date):
        days_to_subtract = (ref_date.weekday() - 5) % 7
        start = ref_date - timedelta(days=days_to_subtract)
        end = start + timedelta(days=5) 
        return start, end

    def open_week_picker_dialog(e):
        current_date = [state["weekly_view_date"]]
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        weeks_col = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, height=280)
        
        def render_weeks():
            weeks_col.controls.clear()
            year = current_date[0].year
            month = current_date[0].month
            first_day = datetime(year, month, 1)
            days_to_subtract = (first_day.weekday() - 5) % 7
            curr_start = first_day - timedelta(days=days_to_subtract)
            active_start, _ = get_week_range(state["weekly_view_date"])
            week_num = 1
            
            while True:
                curr_end = curr_start + timedelta(days=5) 
                if curr_start.month != month and curr_start > first_day: 
                    break
                    
                is_active = (curr_start.date() == active_start.date())
                
                def make_click_handler(st_date):
                    return lambda e: select_week(st_date)

                week_btn = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.DATE_RANGE, color="white" if is_active else COLOR_PRIMARY, size=18), 
                        ft.Text(f"Week {week_num}: {curr_start.strftime('%d %b')} to {curr_end.strftime('%d %b %Y')}", weight="bold", color="white" if is_active else COLOR_TEXT_MAIN, size=14)
                    ]), 
                    padding=ft.padding.symmetric(vertical=12, horizontal=15), 
                    bgcolor=COLOR_PRIMARY if is_active else COLOR_BG_LIGHT, 
                    border_radius=8, 
                    ink=True, 
                    on_click=make_click_handler(curr_start)
                )
                weeks_col.controls.append(week_btn)
                curr_start += timedelta(days=7) 
                week_num += 1
                
            page.update()

        def select_week(start_date):
            state["weekly_view_date"] = start_date
            picker_dlg.open = False
            page.update()
            page.run_thread(load_weekly_tab)
            
        def on_month_year_change(e):
            m_idx = months.index(month_dd.value) + 1
            current_date[0] = datetime(int(year_dd.value), m_idx, 1)
            render_weeks()

        month_dd = ft.Dropdown(
            options=[ft.dropdown.Option(m) for m in months], 
            value=months[current_date[0].month - 1], 
            width=145, 
            border_radius=8, 
            content_padding=10
        )
        year_dd = ft.Dropdown(
            options=[ft.dropdown.Option(str(y)) for y in range(2020, 2035)], 
            value=str(current_date[0].year), 
            width=105, 
            border_radius=8, 
            content_padding=10
        )
        
        month_dd.on_change = on_month_year_change
        year_dd.on_change = on_month_year_change
        
        def close_picker(e):
            picker_dlg.open = False
            page.update()

        picker_dlg = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.CALENDAR_MONTH, color=COLOR_PRIMARY), 
                ft.Text("Select Week", weight="bold", size=18)
            ]), 
            content=ft.Container(
                content=ft.Column([
                    ft.Row([month_dd, year_dd], alignment=ft.MainAxisAlignment.CENTER), 
                    ft.Divider(height=10, color="transparent"), 
                    weeks_col
                ], tight=True), 
                width=320, 
                padding=10
            ), 
            actions=[
                ft.TextButton("Cancel", on_click=close_picker)
            ], 
            shape=ft.RoundedRectangleBorder(radius=12)
        )
        
        def open_dialog_safe(dlg):
            if dlg not in page.overlay:
                page.overlay.append(dlg)
            dlg.open = True
            page.update()
            
        open_dialog_safe(picker_dlg)
        render_weeks()

    month_clickable = ft.Container(
        content=week_label, 
        on_click=open_week_picker_dialog, 
        ink=True, 
        padding=ft.padding.symmetric(horizontal=10, vertical=5), 
        border_radius=5, 
        tooltip="Click to Select Week"
    )

    def get_period_range():
        start, end = get_week_range(state["weekly_view_date"])
        return start, end, f"{start.strftime('%d %b')} - {end.strftime('%d %b %Y')}"

    def change_period_left(e):
        state["weekly_view_date"] += timedelta(weeks=-1)
        page.run_thread(load_weekly_tab)

    def change_period_right(e):
        state["weekly_view_date"] += timedelta(weeks=1)
        page.run_thread(load_weekly_tab)

    def reset_to_this_week(e):
        state["weekly_view_date"] = datetime.now()
        page.run_thread(load_weekly_tab)

    search_input = ft.TextField(
        label="Search Name or ID...", 
        width=250, 
        border_radius=8, 
        content_padding=12, 
        border_color="#D1D5DB", 
        bgcolor="#F9FAFB", 
        height=40, 
        prefix_icon=ft.Icons.SEARCH, 
        on_change=lambda e: load_weekly_tab()
    )

    # MEMORY OPTIMIZED ABSENT CALCULATION
    def calculate_absents_mem(worker_id, all_att):
        att_data = all_att.get(worker_id, [])
        absent_dates = [row[0] for row in att_data if row[2] == "Absent"]
        return len(absent_dates), absent_dates

    def handle_status_click(e, w_name, start, end, current_is_paid, w_id, total_pay, type_str, total_unpaid_ot):
        if current_is_paid: 
            db.delete_period_record(start, end, w_name)
            # Revert overtime back to unpaid
            c = db.conn.cursor()
            c.execute("UPDATE overtime_history SET status='Unpaid' WHERE worker_id=? AND date BETWEEN ? AND ? AND status='Paid'", (w_id, start, end))
            db.conn.commit()
            
            show_snack(page, "Payment Marked as Pending", "orange")
            page.run_thread(load_weekly_tab)
        else: 
            paid_input = ft.TextField(
                label="Amount Paid (PKR)", 
                value=str(int(total_pay) if total_pay > 0 else 0), 
                keyboard_type=ft.KeyboardType.NUMBER, 
                border_color="blue", 
                border_radius=8, 
                autofocus=True
            )
            
            def save_payment(e):
                try: 
                    actual_paid = float(paid_input.value)
                except ValueError: 
                    show_snack(page, "Invalid amount", "red")
                    return
                
                dlg.open = False
                page.update()
                show_snack(page, "Payment Recorded Successfully!", "green")
                
                def background_save():
                    db.save_record(start, end, w_name, type_str, actual_paid)
                    diff = total_pay - actual_paid
                    
                    if diff != 0:
                        next_week_start = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=2) 
                        reason = "Previous Balance Carry Forward" if diff > 0 else "Overpayment Carry Forward"
                        db.add_advance(w_id, -diff, reason, next_week_start.strftime("%Y-%m-%d"))

                    # Synchronize Overtime logic to Paid
                    if total_unpaid_ot > 0:
                        c = db.conn.cursor()
                        c.execute("UPDATE overtime_history SET status='Paid' WHERE worker_id=? AND date BETWEEN ? AND ? AND (status='Unpaid' OR status IS NULL)", (w_id, start, end))
                        db.conn.commit()
                    
                    load_weekly_tab()

                page.run_thread(background_save)

            paid_input.on_submit = save_payment

            def close_payment_dialog(e):
                dlg.open = False
                page.update()

            dlg = ft.AlertDialog(
                title=ft.Text(f"Process Payment: {w_name}", weight="bold"), 
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(f"Calculated Final Salary: {int(total_pay):,} PKR", size=14, weight="bold"), 
                        ft.Text("Enter actual amount paid. Any difference will be carried forward.", size=12, color="grey"), 
                        paid_input
                    ], tight=True), 
                    width=350
                ), 
                actions=[
                    ft.TextButton("Cancel", on_click=close_payment_dialog), 
                    ft.ElevatedButton("Save Payment", on_click=save_payment, bgcolor="#10B981", color="white")
                ]
            )
            
            if dlg not in page.overlay: 
                page.overlay.append(dlg)
            dlg.open = True
            page.update()

    # --- DETAIL DIALOG FUNCTIONS ---
    def open_unpaid_ot_dialog(e, w_id, w_name, start_date, end_date):
        c = db.conn.cursor()
        c.execute("SELECT date, hours, amount FROM overtime_history WHERE worker_id=? AND date BETWEEN ? AND ? AND (status='Unpaid' OR status IS NULL) ORDER BY date", (w_id, start_date, end_date))
        rows = c.fetchall()
        
        list_items = []
        total_ot = 0
        for r in rows:
            total_ot += float(r[2])
            list_items.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(r[0], width=100, size=13),
                        ft.Text(f"{r[1]} hrs", width=80, size=13),
                        ft.Text(f"+{int(r[2])} PKR", weight="bold", color="#10B981", size=13, text_align=ft.TextAlign.RIGHT, expand=True)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=10, border=ft.border.only(bottom=ft.border.BorderSide(1, COLOR_BORDER))
                )
            )
        if not list_items:
            list_items.append(ft.Text("No unpaid overtime records found in this period.", italic=True, color="grey"))
        else:
            list_items.append(ft.Container(content=ft.Row([ft.Text("Total", weight="bold", size=14), ft.Text(f"+{int(total_ot)} PKR", weight="bold", color="#10B981", size=14)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=10, bgcolor="#F9FAFB"))
            
        dlg = ft.AlertDialog(
            title=ft.Text(f"Unpaid OT Details: {w_name}", weight="bold", size=16),
            content=ft.Container(content=ft.Column(list_items, scroll=ft.ScrollMode.AUTO, tight=True), width=400),
            actions=[ft.TextButton("Close", on_click=lambda e: setattr(dlg, 'open', False) or page.update())]
        )
        if dlg not in page.overlay: page.overlay.append(dlg)
        dlg.open = True; page.update()

    def open_prev_bal_dialog(e, w_id, w_name, start_date, end_date):
        c = db.conn.cursor()
        c.execute("SELECT date, amount, reason FROM advances WHERE worker_id=? AND date BETWEEN ? AND ? ORDER BY date", (w_id, start_date, end_date))
        rows = c.fetchall()
        
        list_items = []
        total_bal = 0
        for r in rows:
            if r[2] and "Carry Forward" in r[2]:
                amt = float(r[1])
                total_bal += amt
                color = "#EF4444" if amt > 0 else "#10B981"
                disp_amt = f"-{int(amt)} PKR" if amt > 0 else f"+{abs(int(amt))} PKR"
                list_items.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(r[0], width=90, size=13),
                            ft.Text(r[2], expand=True, size=12, color="grey"),
                            ft.Text(disp_amt, weight="bold", color=color, size=13, text_align=ft.TextAlign.RIGHT)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=10, border=ft.border.only(bottom=ft.border.BorderSide(1, COLOR_BORDER))
                    )
                )
        if not list_items:
            list_items.append(ft.Text("No previous balance records found in this period.", italic=True, color="grey"))
        else:
            final_col = "#EF4444" if total_bal > 0 else "#10B981"
            final_disp = f"-{int(total_bal)} PKR" if total_bal > 0 else f"+{abs(int(total_bal))} PKR"
            list_items.append(ft.Container(content=ft.Row([ft.Text("Total", weight="bold", size=14), ft.Text(final_disp, weight="bold", color=final_col, size=14)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=10, bgcolor="#F9FAFB"))
            
        dlg = ft.AlertDialog(
            title=ft.Text(f"Previous Balance Details: {w_name}", weight="bold", size=16),
            content=ft.Container(content=ft.Column(list_items, scroll=ft.ScrollMode.AUTO, tight=True), width=450),
            actions=[ft.TextButton("Close", on_click=lambda e: setattr(dlg, 'open', False) or page.update())]
        )
        if dlg not in page.overlay: page.overlay.append(dlg)
        dlg.open = True; page.update()

    def open_advances_dialog(e, w_id, w_name, start_date, end_date):
        c = db.conn.cursor()
        c.execute("SELECT date, amount, reason FROM advances WHERE worker_id=? AND date BETWEEN ? AND ? ORDER BY date", (w_id, start_date, end_date))
        rows = c.fetchall()
        
        list_items = []
        total_adv = 0
        for r in rows:
            if not r[2] or "Carry Forward" not in r[2]:
                amt = float(r[1])
                total_adv += amt
                color = "#EF4444" if amt > 0 else "grey"
                disp_amt = f"-{int(amt)} PKR" if amt > 0 else f"{int(amt)} PKR"
                list_items.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(r[0], width=90, size=13),
                            ft.Text(r[2] if r[2] else "N/A", expand=True, size=12, color="grey"),
                            ft.Text(disp_amt, weight="bold", color=color, size=13, text_align=ft.TextAlign.RIGHT)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=10, border=ft.border.only(bottom=ft.border.BorderSide(1, COLOR_BORDER))
                    )
                )
        if not list_items:
            list_items.append(ft.Text("No advances records found in this period.", italic=True, color="grey"))
        else:
            list_items.append(ft.Container(content=ft.Row([ft.Text("Total", weight="bold", size=14), ft.Text(f"-{int(total_adv)} PKR", weight="bold", color="#EF4444", size=14)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=10, bgcolor="#F9FAFB"))
            
        dlg = ft.AlertDialog(
            title=ft.Text(f"Advances Details: {w_name}", weight="bold", size=16),
            content=ft.Container(content=ft.Column(list_items, scroll=ft.ScrollMode.AUTO, tight=True), width=450),
            actions=[ft.TextButton("Close", on_click=lambda e: setattr(dlg, 'open', False) or page.update())]
        )
        if dlg not in page.overlay: page.overlay.append(dlg)
        dlg.open = True; page.update()

    def open_absent_dialog(e, w_id, w_name, abs_count, absent_dates):
        if not absent_dates:
            dates_ui = ft.Text("No absences recorded.", italic=True, color="grey")
        else:
            date_controls = []
            for d in absent_dates:
                date_controls.append(ft.Text(f"• {d}", size=14, color="#EF4444", weight="bold"))
            dates_ui = ft.Column(date_controls, spacing=4, scroll=ft.ScrollMode.AUTO, height=120)
            
        def close_absent_dialog(e):
            dlg.open = False
            page.update()
            
        dlg = ft.AlertDialog(
            title=ft.Text(f"Absent Details: {w_name}", weight="bold"), 
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Total Absent Days: {abs_count}", color="red", weight="bold"), 
                    dates_ui, 
                    ft.Divider(height=10, color="transparent"), 
                    ft.Text("Absents do not negatively affect weekly worker pay. Pay is based strictly on present days.", size=11, color="grey")
                ], tight=True), 
                width=350
            ), 
            actions=[
                ft.TextButton("Close", on_click=close_absent_dialog)
            ]
        )
        
        if dlg not in page.overlay: 
            page.overlay.append(dlg)
        dlg.open = True
        page.update()

    def load_weekly_tab(e=None):
        new_list_controls = []
        
        start, end, lbl = get_period_range()
        start_sql = start.strftime("%Y-%m-%d")
        end_sql = end.strftime("%Y-%m-%d")
        week_label.value = lbl
        
        query = search_input.value.lower() if search_input.value else ""

        # --- BULK FETCHING TO PREVENT LAG ---
        c = db.conn.cursor()
        
        c.execute("SELECT * FROM workers WHERE salary_type='Weekly'")
        workers = c.fetchall()
        
        c.execute("SELECT worker_id, date, amount_earned, status FROM attendance WHERE date BETWEEN ? AND ?", (start_sql, end_sql))
        all_att = {}
        for r in c.fetchall():
            all_att.setdefault(r[0], []).append((r[1], r[2], r[3]))
            
        c.execute("SELECT worker_id, amount, reason FROM advances WHERE date BETWEEN ? AND ?", (start_sql, end_sql))
        all_adv = {}
        for r in c.fetchall():
            all_adv.setdefault(r[0], []).append((r[1], r[2]))
            
        # ONLY Fetch Unpaid Overtime for the final salary calculation
        c.execute("SELECT worker_id, SUM(amount) FROM overtime_history WHERE date BETWEEN ? AND ? AND (status='Unpaid' OR status IS NULL) GROUP BY worker_id", (start_sql, end_sql))
        all_unpaid_ot = {r[0]: r[1] for r in c.fetchall()}
        
        c.execute("SELECT worker_name FROM records WHERE period_start=? AND period_end=? AND salary_type='Weekly'", (start_sql, end_sql))
        paid_workers = {r[0] for r in c.fetchall()}
        # ------------------------------------

        header_row = ft.Row([
            ft.Text("ID", width=50, weight="bold", color=COLOR_TEXT_SUB, size=13),
            ft.Text("Name", width=140, weight="bold", color=COLOR_TEXT_SUB, size=13),
            ft.Text("Per Day", width=70, weight="bold", color=COLOR_TEXT_SUB, size=13),
            ft.Text("Absents", width=110, weight="bold", color="#F59E0B", size=13), 
            ft.Text("Unpaid OT", width=95, weight="bold", color="#10B981", size=13),
            ft.Text("Prev Bal", width=95, weight="bold", color="#3B82F6", size=13),
            ft.Text("Advances", width=85, weight="bold", color="#EF4444", size=13),
            ft.Container(expand=True),
            ft.Text("Final", width=110, weight="bold", color="#10B981", size=13),
            ft.Text("Status", width=100, weight="bold", color=COLOR_TEXT_SUB, size=13, text_align=ft.TextAlign.CENTER),
        ])
        
        new_list_controls.append(
            ft.Container(
                content=header_row,
                bgcolor=COLOR_BG_LIGHT, 
                padding=ft.padding.symmetric(vertical=10, horizontal=15), 
                border=ft.border.only(bottom=ft.border.BorderSide(2, COLOR_BORDER))
            )
        )
        
        visible_index = 0
        for w in workers:
            w_id = w[0]
            w_name = w[1]
            w_base = w[7]
            w_custom_id = w[8]
            display_id = f"W-{w_custom_id}"
            
            if query and query not in w_name.lower() and query not in display_id.lower(): 
                continue

            per_day = w_base if w_base else 0

            adv_list = all_adv.get(w_id, [])
            carry_forward = sum(float(a[0]) for a in adv_list if a[1] and "Carry Forward" in a[1])
            standard_adv = sum(float(a[0]) for a in adv_list if not a[1] or "Carry Forward" not in a[1])
            
            absent_count, absent_dates = calculate_absents_mem(w_id, all_att)
            
            att_data = all_att.get(w_id, [])
            earned = sum(float(row[1]) for row in att_data if row[2] == "Present")
            
            overtime_unpaid_amt = all_unpaid_ot.get(w_id, 0.0)
            
            # Final calculation includes base earned + overtime (unpaid) - advances
            final = earned - carry_forward - standard_adv + overtime_unpaid_amt
            is_paid = w_name in paid_workers
            
            def make_status_click(wid, wname, final_amt, paid_status, ot_amt):
                return lambda e: handle_status_click(e, wname, start_sql, end_sql, paid_status, wid, final_amt, "Weekly", ot_amt)

            status_btn = ft.Container(
                content=ft.Text("PAID" if is_paid else "PENDING", size=11, weight="bold", color="white", text_align=ft.TextAlign.CENTER),
                bgcolor="#10B981" if is_paid else "#EF4444", 
                padding=ft.padding.symmetric(horizontal=12, vertical=6), 
                border_radius=5, 
                on_click=make_status_click(w_id, w_name, final, is_paid, overtime_unpaid_amt),
                ink=True, 
                width=100
            )

            absent_btn = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.EVENT_BUSY, color="#F59E0B", size=14), 
                    ft.Text(f"{absent_count} D", color="#F59E0B", weight="bold", size=12)
                ], alignment=ft.MainAxisAlignment.START, spacing=4), 
                on_click=lambda e, wid=w_id, wn=w_name, acount=absent_count, adates=absent_dates: open_absent_dialog(e, wid, wn, acount, adates), 
                tooltip="Click to view dates", 
                ink=True, 
                width=110
            )

            if carry_forward < 0: 
                prev_disp = f"+{abs(int(carry_forward)):,}"
                prev_col = "#10B981"
            elif carry_forward > 0: 
                prev_disp = f"-{int(carry_forward):,}"
                prev_col = "#EF4444"
            else: 
                prev_disp = "0"
                prev_col = "grey"
                
            prev_btn = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.ACCOUNT_BALANCE, size=14, color=prev_col),
                    ft.Text(prev_disp, color=prev_col, weight="bold", size=13)
                ], spacing=4), 
                width=95, ink=True, tooltip="View Carry Forward Details",
                on_click=lambda e, wid=w_id, wn=w_name: open_prev_bal_dialog(e, wid, wn, start_sql, end_sql)
            )

            adv_display = f"-{int(standard_adv):,}" if standard_adv > 0 else f"+{abs(int(standard_adv)):,}" if standard_adv < 0 else "-0"
            adv_color = "#EF4444" if standard_adv > 0 else "grey"
            
            advances_btn = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.MONEY_OFF, size=14, color=adv_color),
                    ft.Text(adv_display, color=adv_color, weight="bold", size=13)
                ], spacing=4), 
                width=85, ink=True, tooltip="View Advances Details",
                on_click=lambda e, wid=w_id, wn=w_name: open_advances_dialog(e, wid, wn, start_sql, end_sql)
            )
            
            ot_display = f"+{int(overtime_unpaid_amt):,}" if overtime_unpaid_amt > 0 else "0"
            ot_color = "#10B981" if overtime_unpaid_amt > 0 else "grey"
            
            ot_btn = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.MORE_TIME, size=14, color=ot_color),
                    ft.Text(ot_display, color=ot_color, weight="bold", size=13)
                ], spacing=4), 
                width=95, ink=True, tooltip="View Unpaid OT Details",
                on_click=lambda e, wid=w_id, wn=w_name: open_unpaid_ot_dialog(e, wid, wn, start_sql, end_sql)
            )

            final_color = "#10B981" if final >= 0 else "#EF4444"

            # FAST HOVER EFFECT
            def make_hover(idx):
                def hover(e):
                    e.control.bgcolor = "#F1F5F9" if e.data == "true" else ("white" if idx % 2 == 0 else "#FAFAFA")
                    e.control.update() 
                return hover

            worker_row = ft.Row([
                ft.Text(display_id, width=50, weight="w600", color=COLOR_TEXT_MAIN, size=13),
                ft.Text(w_name, width=140, weight="bold", color=COLOR_TEXT_MAIN, size=15),
                ft.Text(f"{int(per_day):,}", width=70, color=COLOR_TEXT_SUB, size=13),
                absent_btn, 
                ot_btn, 
                prev_btn, 
                advances_btn,
                ft.Container(expand=True), 
                ft.Text(f"{int(final):,} PKR", width=110, weight="bold", color=final_color, size=15),
                ft.Container(content=status_btn, width=100)
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER)

            worker_container = ft.Container(
                content=worker_row, 
                padding=ft.padding.symmetric(vertical=8, horizontal=15), 
                bgcolor="white" if visible_index % 2 == 0 else "#FAFAFA", 
                border=ft.border.only(bottom=ft.border.BorderSide(1, COLOR_BORDER)), 
                on_hover=make_hover(visible_index)
            )

            new_list_controls.append(worker_container)
            visible_index += 1
            
        weekly_grid.controls = new_list_controls
        page.update()
    
    def finalize_week(e):
        def background_finalize():
            start, end, _ = get_period_range()
            start_sql = start.strftime("%Y-%m-%d")
            end_sql = end.strftime("%Y-%m-%d")
            
            c = db.conn.cursor()
            
            c.execute("SELECT * FROM workers WHERE salary_type='Weekly'")
            workers = c.fetchall()
            
            c.execute("SELECT worker_id, amount FROM advances WHERE date BETWEEN ? AND ?", (start_sql, end_sql))
            all_adv = {}
            for r in c.fetchall(): all_adv.setdefault(r[0], []).append(r[1])
            
            c.execute("SELECT worker_id, amount_earned, status FROM attendance WHERE date BETWEEN ? AND ?", (start_sql, end_sql))
            all_att = {}
            for r in c.fetchall(): all_att.setdefault(r[0], []).append((r[1], r[2]))
            
            c.execute("SELECT worker_id, SUM(amount) FROM overtime_history WHERE date BETWEEN ? AND ? AND (status='Unpaid' OR status IS NULL) GROUP BY worker_id", (start_sql, end_sql))
            all_unpaid_ot = {r[0]: r[1] for r in c.fetchall()}
            
            c.execute("SELECT worker_name FROM records WHERE period_start=? AND period_end=? AND salary_type='Weekly'", (start_sql, end_sql))
            paid_workers = {r[0] for r in c.fetchall()}

            for w in workers:
                w_id = w[0]
                w_name = w[1]
                
                adv_list = all_adv.get(w_id, [])
                adv = sum(float(a) for a in adv_list) 
                
                att_data = all_att.get(w_id, [])
                earned = sum(float(row[0]) for row in att_data if row[1] == "Present")
                
                overtime_unpaid_amt = all_unpaid_ot.get(w_id, 0.0)
                final = earned - adv + overtime_unpaid_amt
                
                is_paid = w_name in paid_workers
                
                if not is_paid:
                    actual_paid = final if final > 0 else 0
                    db.save_record(start_sql, end_sql, w_name, "Weekly", actual_paid)
                    diff = final - actual_paid
                    
                    if diff != 0:
                        next_week_start = datetime.strptime(end_sql, "%Y-%m-%d") + timedelta(days=2)
                        reason = "Previous Balance Carry Forward" if diff > 0 else "Overpayment Carry Forward"
                        db.add_advance(w_id, -diff, reason, next_week_start.strftime("%Y-%m-%d"))
                    
                    if overtime_unpaid_amt > 0:
                        c.execute("UPDATE overtime_history SET status='Paid' WHERE worker_id=? AND date BETWEEN ? AND ? AND (status='Unpaid' OR status IS NULL)", (w_id, start_sql, end_sql))
                        db.conn.commit()
                        
            show_snack(page, "Successfully Saved!", "green")
            load_weekly_tab()
            
        page.run_thread(background_finalize)

    top_row = ft.Row([
        ft.Text("Weekly View", size=22, weight="bold", color=COLOR_TEXT_MAIN),
        ft.Row([
            ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=change_period_left),
            month_clickable,
            ft.IconButton(icon=ft.Icons.ARROW_FORWARD, on_click=change_period_right),
            ft.TextButton("This Week", icon=ft.Icons.TODAY, on_click=reset_to_this_week, style=ft.ButtonStyle(color=COLOR_PRIMARY))
        ], alignment=ft.MainAxisAlignment.CENTER),
        ft.Row([
            search_input, 
            ft.FilledButton("Finalize All", icon=ft.Icons.SAVE, on_click=finalize_week, bgcolor="#111827")
        ], spacing=10)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    grid_container = ft.Container(
        content=weekly_grid, 
        expand=True, 
        bgcolor="white", 
        border_radius=8, 
        border=ft.border.all(1, COLOR_BORDER), 
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=2, color="#0D000000", offset=ft.Offset(0, 1)), 
        clip_behavior=ft.ClipBehavior.HARD_EDGE
    )

    weekly_container = ft.Container(
        content=ft.Column([
            top_row, 
            ft.Divider(height=5, color="transparent"),
            grid_container
        ], expand=True), 
        visible=False
    )

    return weekly_container, load_weekly_tab