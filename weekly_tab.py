import flet as ft
from datetime import datetime, timedelta
# Import our new professional export module
from exports import export_weekly_summary_to_excel

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
                    padding=ft.Padding.symmetric(vertical=12, horizontal=15), 
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
        padding=ft.Padding.symmetric(horizontal=10, vertical=5), 
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

    def calculate_absents_mem(worker_id, all_att):
        att_data = all_att.get(worker_id, [])
        absent_dates = [row[0] for row in att_data if row[2] == "Absent"]
        return len(absent_dates), absent_dates

    def handle_status_click(e, w_name, start, end, current_is_paid, w_id, total_pay, type_str, total_unpaid_ot):
        if current_is_paid: 
            db.delete_period_record(start, end, w_name)
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
            
            try:
                paid_input.selection = ft.TextSelection(0, len(paid_input.value))
            except AttributeError: pass
            
            def save_payment(e=None):
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
            
            def open_dialog_safe_local(dlg):
                if dlg not in page.overlay: page.overlay.append(dlg)
                dlg.open = True; page.update()
                
            open_dialog_safe_local(dlg)

    # --- SHARED PROFESSIONAL DETAIL TABLES ---
    def build_ot_detail_table(rows):
        list_items = [
            ft.Container(
                content=ft.Row([
                    ft.Text("Date", width=90, weight="bold", size=12, color=COLOR_TEXT_SUB),
                    ft.Text("Shift/Type", width=90, weight="bold", size=12, color=COLOR_TEXT_SUB),
                    ft.Text("Hours", width=60, weight="bold", size=12, color=COLOR_TEXT_SUB),
                    ft.Text("Amount", weight="bold", size=12, color=COLOR_TEXT_SUB, text_align=ft.TextAlign.RIGHT, expand=True)
                ]),
                padding=ft.Padding.only(bottom=10, left=10, right=10),
                border=ft.border.only(bottom=ft.border.BorderSide(2, COLOR_BORDER))
            )
        ]
        
        total_amt = 0
        for r in rows:
            date_str = r[0]
            hrs = float(r[1])
            amt = float(r[2])
            shift = r[3] if len(r) > 3 and r[3] else "--"
            
            total_amt += amt
            
            if shift == "Payment" or hrs == 0:
                shift_disp = "Adjustment"
                hrs_disp = "--"
            else:
                shift_disp = shift
                hrs_disp = f"{hrs:g} h"

            amt_color = "#10B981" if amt >= 0 else "#EF4444"
            prefix = "+" if amt >= 0 else ""
            
            list_items.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(date_str, width=90, size=13),
                        ft.Text(shift_disp, width=90, size=12, color="grey"),
                        ft.Text(hrs_disp, width=60, size=13),
                        ft.Text(f"{prefix}{int(amt)} PKR", weight="bold", color=amt_color, size=13, text_align=ft.TextAlign.RIGHT, expand=True)
                    ]),
                    padding=10, border=ft.border.only(bottom=ft.border.BorderSide(1, COLOR_BORDER))
                )
            )
        
        if len(list_items) == 1:
            list_items.append(ft.Container(content=ft.Text("No records found.", italic=True, color="grey"), padding=10))
        else:
            list_items.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text("Total", weight="bold", size=14), 
                        ft.Text(f"{int(total_amt)} PKR", weight="bold", color="#10B981" if total_amt >= 0 else "#EF4444", size=14)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
                    padding=10, bgcolor="#F9FAFB"
                )
            )
        return list_items

    def build_adv_table(rows, is_prev_bal=False):
        list_items = [
            ft.Container(
                content=ft.Row([
                    ft.Text("Date", width=90, weight="bold", size=12, color=COLOR_TEXT_SUB),
                    ft.Text("Reason", weight="bold", size=12, color=COLOR_TEXT_SUB, expand=True),
                    ft.Text("Amount", width=100, weight="bold", size=12, color=COLOR_TEXT_SUB, text_align=ft.TextAlign.RIGHT)
                ]),
                padding=ft.Padding.only(bottom=10, left=10, right=10),
                border=ft.border.only(bottom=ft.border.BorderSide(2, COLOR_BORDER))
            )
        ]
        
        total_amt = 0
        filtered_rows = []
        for r in rows:
            rsn = r[2] if r[2] else ""
            if is_prev_bal and "Carry Forward" not in rsn: continue
            if not is_prev_bal and "Carry Forward" in rsn: continue
            filtered_rows.append(r)

        for r in filtered_rows:
            date_str = r[0]
            amt = float(r[1])
            rsn = r[2] if r[2] else "--"
            total_amt += amt
            
            color = "#EF4444" if amt > 0 else "#10B981"
            prefix = "-" if amt > 0 else "+"
            
            list_items.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(date_str, width=90, size=13),
                        ft.Text(rsn, size=12, color="grey", expand=True),
                        ft.Text(f"{prefix}{abs(int(amt))} PKR", weight="bold", color=color, size=13, text_align=ft.TextAlign.RIGHT)
                    ]),
                    padding=10, border=ft.border.only(bottom=ft.border.BorderSide(1, COLOR_BORDER))
                )
            )
            
        if not filtered_rows:
            list_items.append(ft.Container(content=ft.Text("No records found.", italic=True, color="grey"), padding=10))
        else:
            final_color = "#EF4444" if total_amt > 0 else "#10B981"
            final_prefix = "-" if total_amt > 0 else "+"
            if total_amt == 0: final_prefix = ""; final_color = "grey"
            
            list_items.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text("Total", weight="bold", size=14), 
                        ft.Text(f"{final_prefix}{abs(int(total_amt))} PKR", weight="bold", color=final_color, size=14)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
                    padding=10, bgcolor="#F9FAFB"
                )
            )
        return list_items

    # --- DETAIL DIALOG FUNCTIONS ---
    def open_unpaid_ot_dialog(e, w_id, w_name, start_date, end_date):
        c = db.conn.cursor()
        c.execute("SELECT date, hours, amount, shift FROM overtime_history WHERE worker_id=? AND date BETWEEN ? AND ? AND (status='Unpaid' OR status IS NULL) ORDER BY date", (w_id, start_date, end_date))
        rows = c.fetchall()
        list_items = build_ot_detail_table(rows)
            
        dlg = ft.AlertDialog(
            title=ft.Text(f"Unpaid OT Details: {w_name}", weight="bold", size=16),
            content=ft.Container(content=ft.Column(list_items, scroll=ft.ScrollMode.AUTO, tight=True), width=450),
            actions=[ft.TextButton("Close", on_click=lambda e: setattr(dlg, 'open', False) or page.update())]
        )
        def open_dialog_safe_local(dlg):
            if dlg not in page.overlay: page.overlay.append(dlg)
            dlg.open = True; page.update()
        open_dialog_safe_local(dlg)

    def open_prev_bal_dialog(e, w_id, w_name, start_date, end_date):
        c = db.conn.cursor()
        c.execute("SELECT date, amount, reason FROM advances WHERE worker_id=? AND date BETWEEN ? AND ? ORDER BY date", (w_id, start_date, end_date))
        rows = c.fetchall()
        list_items = build_adv_table(rows, is_prev_bal=True)
            
        dlg = ft.AlertDialog(
            title=ft.Text(f"Previous Balance: {w_name}", weight="bold", size=16),
            content=ft.Container(content=ft.Column(list_items, scroll=ft.ScrollMode.AUTO, tight=True), width=450),
            actions=[ft.TextButton("Close", on_click=lambda e: setattr(dlg, 'open', False) or page.update())]
        )
        def open_dialog_safe_local(dlg):
            if dlg not in page.overlay: page.overlay.append(dlg)
            dlg.open = True; page.update()
        open_dialog_safe_local(dlg)

    def open_advances_dialog(e, w_id, w_name, start_date, end_date):
        c = db.conn.cursor()
        c.execute("SELECT date, amount, reason FROM advances WHERE worker_id=? AND date BETWEEN ? AND ? ORDER BY date", (w_id, start_date, end_date))
        rows = c.fetchall()
        list_items = build_adv_table(rows, is_prev_bal=False)
            
        dlg = ft.AlertDialog(
            title=ft.Text(f"Advances Details: {w_name}", weight="bold", size=16),
            content=ft.Container(content=ft.Column(list_items, scroll=ft.ScrollMode.AUTO, tight=True), width=450),
            actions=[ft.TextButton("Close", on_click=lambda e: setattr(dlg, 'open', False) or page.update())]
        )
        def open_dialog_safe_local(dlg):
            if dlg not in page.overlay: page.overlay.append(dlg)
            dlg.open = True; page.update()
        open_dialog_safe_local(dlg)

    # --- EXCEL / SUMMARY EXPORT/DIALOG LOGIC ---
    def open_summary_dialog(e, w_id, w_name, start_date, end_date, include_advances=False):
        c = db.conn.cursor()
        
        c.execute("SELECT date, status, amount_earned FROM attendance WHERE worker_id=? AND date BETWEEN ? AND ?", (w_id, start_date, end_date))
        att_map = {r[0]: {"status": r[1], "earned": float(r[2])} for r in c.fetchall()}
        
        c.execute("SELECT date, SUM(hours), SUM(amount) FROM overtime_history WHERE worker_id=? AND date BETWEEN ? AND ? AND (status='Unpaid' OR status IS NULL) GROUP BY date", (w_id, start_date, end_date))
        ot_map = {r[0]: {"hrs": float(r[1]), "amt": float(r[2])} for r in c.fetchall()}
        
        if include_advances:
            # TRIGGERED BY NAME CLICK - Call our new export module
            export_weekly_summary_to_excel(db, w_id, w_name, start_date, end_date, page, show_snack)
                
        else:
            # THIS IS TRIGGERED BY FINAL AMOUNT CLICK - SHOW FLET UI DIALOG (No Advances)
            columns = [
                ft.DataColumn(ft.Text("Date", weight="bold", size=13)),
                ft.DataColumn(ft.Text("Status", weight="bold", size=13)),
                ft.DataColumn(ft.Text("Base Pay", weight="bold", size=13, text_align=ft.TextAlign.RIGHT)),
                ft.DataColumn(ft.Text("OT Hrs", weight="bold", size=13, text_align=ft.TextAlign.RIGHT)),
                ft.DataColumn(ft.Text("OT Pay", weight="bold", size=13, text_align=ft.TextAlign.RIGHT)),
                ft.DataColumn(ft.Text("Daily Total", weight="bold", size=13, text_align=ft.TextAlign.RIGHT))
            ]

            rows = []
            curr = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            
            total_base = 0
            total_ot = 0
            
            while curr <= end:
                d_str = curr.strftime("%Y-%m-%d")
                
                att = att_map.get(d_str, {"status": "Not Marked", "earned": 0.0})
                ot = ot_map.get(d_str, {"hrs": 0.0, "amt": 0.0})
                
                total_base += att["earned"]
                total_ot += ot["amt"]
                
                status_color = "#10B981" if att["status"] == "Present" else ("#EF4444" if att["status"] == "Absent" else "grey")
                daily_tot = att["earned"] + ot["amt"]
                
                cells = [
                    ft.DataCell(ft.Text(d_str, size=13, weight="w500")),
                    ft.DataCell(ft.Text(att["status"], color=status_color, size=12, weight="bold")),
                    ft.DataCell(ft.Text(f"{int(att['earned'])}", size=13)),
                    ft.DataCell(ft.Text(f"{ot['hrs']:g} h" if ot['hrs'] > 0 else "--", size=13, color=COLOR_PRIMARY if ot['hrs'] > 0 else "grey")),
                    ft.DataCell(ft.Text(f"+{int(ot['amt'])}" if ot['amt'] > 0 else "--", size=13, weight="bold" if ot['amt'] > 0 else "normal", color="#10B981" if ot['amt'] > 0 else "grey")),
                    ft.DataCell(ft.Text(f"{int(daily_tot)}", size=13, weight="bold", color="#10B981"))
                ]
                rows.append(ft.DataRow(cells=cells))
                curr += timedelta(days=1)
                
            sum_cells = [
                ft.DataCell(ft.Text("TOTAL", weight="bold", size=14)),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text(f"{int(total_base)}", weight="bold", size=14)),
                ft.DataCell(ft.Text("")),
                ft.DataCell(ft.Text(f"+{int(total_ot)}", weight="bold", color="#10B981", size=14)),
                ft.DataCell(ft.Text(f"{int(total_base + total_ot)}", weight="bold", color="#10B981", size=14))
            ]
            rows.append(ft.DataRow(cells=sum_cells))

            dt = ft.DataTable(
                columns=columns,
                rows=rows,
                heading_row_height=40,
                data_row_min_height=35,
                data_row_max_height=35,
                border=ft.border.all(1, COLOR_BORDER)
            )
            
            dlg = ft.AlertDialog(
                title=ft.Text(f"Daily Payout Breakdown: {w_name}", weight="bold", size=18),
                content=ft.Container(content=ft.Column([dt], scroll=ft.ScrollMode.AUTO, tight=True), width=550),
                actions=[ft.TextButton("Close", on_click=lambda e: setattr(dlg, 'open', False) or page.update())]
            )
            def open_dialog_safe_local(dlg):
                if dlg not in page.overlay: page.overlay.append(dlg)
                dlg.open = True; page.update()
            open_dialog_safe_local(dlg)


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
        
        def open_dialog_safe_local(dlg):
            if dlg not in page.overlay: page.overlay.append(dlg)
            dlg.open = True; page.update()
        open_dialog_safe_local(dlg)

    def load_weekly_tab(e=None):
        new_list_controls = []
        
        start, end, lbl = get_period_range()
        start_sql = start.strftime("%Y-%m-%d")
        end_sql = end.strftime("%Y-%m-%d")
        week_label.value = lbl
        
        query = search_input.value.lower() if search_input.value else ""

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
            
        c.execute("SELECT worker_id, SUM(amount) FROM overtime_history WHERE date BETWEEN ? AND ? AND (status='Unpaid' OR status IS NULL) GROUP BY worker_id", (start_sql, end_sql))
        all_unpaid_ot = {r[0]: r[1] for r in c.fetchall()}
        
        c.execute("SELECT worker_name FROM records WHERE period_start=? AND period_end=? AND salary_type='Weekly'", (start_sql, end_sql))
        paid_workers = {r[0] for r in c.fetchall()}

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
                padding=ft.Padding.symmetric(vertical=10, horizontal=15), 
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
            
            final = earned - carry_forward - standard_adv + overtime_unpaid_amt
            is_paid = w_name in paid_workers
            
            def make_status_click(wid, wname, final_amt, paid_status, ot_amt):
                return lambda e: handle_status_click(e, wname, start_sql, end_sql, paid_status, wid, final_amt, "Weekly", ot_amt)

            status_btn = ft.Container(
                content=ft.Text("PAID" if is_paid else "PENDING", size=11, weight="bold", color="white", text_align=ft.TextAlign.CENTER),
                bgcolor="#10B981" if is_paid else "#EF4444", 
                padding=ft.Padding.symmetric(horizontal=12, vertical=6), 
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

            # EXCEL & SUMMARY CLICKS
            name_btn = ft.Container(
                content=ft.Text(w_name, weight="bold", color=COLOR_TEXT_MAIN, size=15),
                ink=True, on_click=lambda e, wid=w_id, wn=w_name: open_summary_dialog(e, wid, wn, start_sql, end_sql, include_advances=True),
                tooltip="Open Full Excel Summary"
            )

            final_btn = ft.Container(
                content=ft.Text(f"{int(final):,} PKR", weight="bold", color=final_color, size=15),
                ink=True, on_click=lambda e, wid=w_id, wn=w_name: open_summary_dialog(e, wid, wn, start_sql, end_sql, include_advances=False),
                tooltip="View Daily Payout Breakdown"
            )

            def make_hover(idx):
                def hover(e):
                    e.control.bgcolor = "#F1F5F9" if e.data == "true" else ("white" if idx % 2 == 0 else "#FAFAFA")
                    e.control.update() 
                return hover

            worker_row = ft.Row([
                ft.Text(display_id, width=50, weight="w600", color=COLOR_TEXT_MAIN, size=13),
                ft.Container(content=name_btn, width=140),
                ft.Text(f"{int(per_day):,}", width=70, color=COLOR_TEXT_SUB, size=13),
                absent_btn, 
                ot_btn, 
                prev_btn, 
                advances_btn,
                ft.Container(expand=True), 
                ft.Container(content=final_btn, width=110),
                ft.Container(content=status_btn, width=100)
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER)

            worker_container = ft.Container(
                content=worker_row, 
                padding=ft.Padding.symmetric(vertical=8, horizontal=15), 
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
            ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, on_click=change_period_left),
            month_clickable,
            ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, on_click=change_period_right),
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