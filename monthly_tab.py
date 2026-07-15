import flet as ft
from datetime import datetime, timedelta

def get_monthly_view(page: ft.Page, db, state, show_snack, open_dialog_safe):
    COLOR_TEXT_MAIN = "#111827"
    COLOR_TEXT_SUB = "#4B5563"
    COLOR_BORDER = "#E5E7EB"
    COLOR_BG_LIGHT = "#F3F4F6"
    COLOR_PRIMARY = "#2D5B7A"
    
    monthly_grid = ft.ListView(spacing=0, expand=True)
    month_label = ft.Text("", size=16, weight="bold")

    if "absent_penalties" not in state: 
        state["absent_penalties"] = {}
        
    if "mon_view_mode" not in state:
        state["mon_view_mode"] = "Month"
        state["mon_view_date"] = datetime.now()

    def open_filter_dialog(e):
        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        
        month_dd = ft.Dropdown(
            options=[ft.dropdown.Option(m) for m in months], 
            value=state["mon_view_date"].strftime("%B"), 
            width=145, 
            border_radius=8, 
            content_padding=10
        )
        
        year_dd = ft.Dropdown(
            options=[ft.dropdown.Option(str(y)) for y in range(2020, 2035)], 
            value=state["mon_view_date"].strftime("%Y"), 
            width=145, 
            border_radius=8, 
            content_padding=10
        )
        
        month_row = ft.Row([month_dd, year_dd], alignment=ft.MainAxisAlignment.CENTER)

        def apply_filter(e):
            selected_month_idx = months.index(month_dd.value) + 1
            selected_year = int(year_dd.value)
            state["mon_view_date"] = datetime(selected_year, selected_month_idx, 1)
            filter_dialog.open = False
            page.update()
            page.run_thread(load_monthly_tab)

        def close_filter(e):
            filter_dialog.open = False
            page.update()

        filter_dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.CALENDAR_MONTH, color=COLOR_PRIMARY), 
                ft.Text("Select Month", weight="bold", size=18)
            ]),
            content=ft.Container(
                content=ft.Column([month_row], tight=True), 
                width=320, 
                padding=10
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_filter), 
                ft.ElevatedButton("Apply Filter", bgcolor=COLOR_PRIMARY, color="white", on_click=apply_filter)
            ], 
            shape=ft.RoundedRectangleBorder(radius=12)
        )
        open_dialog_safe(page, filter_dialog)

    month_clickable = ft.Container(
        content=month_label, 
        on_click=open_filter_dialog, 
        ink=True, 
        padding=ft.padding.symmetric(horizontal=10, vertical=5), 
        border_radius=5, 
        tooltip="Click to Change Month"
    )

    def get_period_range():
        start = state["mon_view_date"].replace(day=1)
        next_m = start.replace(day=28) + timedelta(days=4)
        end = next_m - timedelta(days=next_m.day)
        return start, end, start.strftime("%B %Y")

    def change_period_left(e):
        curr = state["mon_view_date"]
        new_m = curr.month - 1
        y_adj = 0
        if new_m < 1: 
            new_m = 12
            y_adj = -1
        state["mon_view_date"] = curr.replace(month=new_m, year=curr.year + y_adj)
        page.run_thread(load_monthly_tab)

    def change_period_right(e):
        curr = state["mon_view_date"]
        new_m = curr.month + 1
        y_adj = 0
        if new_m > 12: 
            new_m = 1
            y_adj = 1
        state["mon_view_date"] = curr.replace(month=new_m, year=curr.year + y_adj)
        page.run_thread(load_monthly_tab)

    def reset_to_today(e):
        state["mon_view_date"] = datetime.now()
        page.run_thread(load_monthly_tab)
        page.update()

    def calculate_absents_mem(worker_id, start_dt, end_dt, all_att):
        att_data = all_att.get(worker_id, [])
        att_status_map = {row[0]: row[2] for row in att_data}
        
        absent_dates = []
        curr = start_dt
        while curr <= end_dt:
            d_str = curr.strftime("%Y-%m-%d")
            status = att_status_map.get(d_str, "Not Marked")
            
            if curr.weekday() == 4: # Friday
                thu = (curr - timedelta(days=1)).strftime("%Y-%m-%d")
                sat = (curr + timedelta(days=1)).strftime("%Y-%m-%d")
                
                thu_status = att_status_map.get(thu, "Not Marked")
                sat_status = att_status_map.get(sat, "Not Marked")
                
                if thu_status == "Absent" or sat_status == "Absent":
                    friday_rule_str = f"{d_str} (Friday Rule)"
                    if friday_rule_str not in absent_dates and d_str not in absent_dates: 
                        absent_dates.append(friday_rule_str)
                elif status == "Absent" and d_str not in absent_dates: 
                    absent_dates.append(d_str)
            else:
                if status == "Absent" and d_str not in absent_dates: 
                    absent_dates.append(d_str)
                    
            curr += timedelta(days=1)
            
        return len(absent_dates), absent_dates

    def handle_status_click(e, w_name, start, end, current_is_paid, w_id, total_pay, type_str, total_unpaid_ot):
        if current_is_paid: 
            db.delete_period_record(start, end, w_name)
            # Revert overtime back to unpaid
            c = db.conn.cursor()
            c.execute("UPDATE overtime_history SET status='Unpaid' WHERE worker_id=? AND date BETWEEN ? AND ? AND status='Paid'", (w_id, start, end))
            db.conn.commit()
            
            show_snack(page, "Payment Marked as Pending", "orange")
            page.run_thread(load_monthly_tab)
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
                    show_snack(page, "Invalid amount format.", "red")
                    return
                    
                dlg.open = False
                page.update()
                show_snack(page, "Payment Recorded!", "green")
                
                def background_save():
                    db.save_record(start, end, w_name, type_str, actual_paid)
                    diff = total_pay - actual_paid
                    
                    if diff != 0:
                        curr_start = datetime.strptime(start, "%Y-%m-%d")
                        next_month_start = (curr_start.replace(day=28) + timedelta(days=4)).replace(day=1)
                        reason = "Previous Balance Carry Forward" if diff > 0 else "Overpayment Carry Forward"
                        db.add_advance(w_id, -diff, reason, next_month_start.strftime("%Y-%m-%d"))
                        
                    # Synchronize Overtime logic to Paid
                    if total_unpaid_ot > 0:
                        c = db.conn.cursor()
                        c.execute("UPDATE overtime_history SET status='Paid' WHERE worker_id=? AND date BETWEEN ? AND ? AND (status='Unpaid' OR status IS NULL)", (w_id, start, end))
                        db.conn.commit()
                        
                    load_monthly_tab()

                page.run_thread(background_save)
                
            paid_input.on_submit = save_payment

            def close_payment(e):
                dlg.open = False
                page.update()

            dlg = ft.AlertDialog(
                title=ft.Text(f"Process Payment: {w_name}", weight="bold"), 
                content=ft.Container(
                    content=ft.Column([
                        ft.Text(f"Calculated Final Salary: {int(total_pay):,} PKR", size=14, weight="bold"), 
                        ft.Text("Enter actual amount paid.", size=12, color="grey"), 
                        paid_input
                    ], tight=True), 
                    width=350
                ), 
                actions=[
                    ft.TextButton("Cancel", on_click=close_payment), 
                    ft.ElevatedButton("Save Payment", on_click=save_payment, bgcolor="#10B981", color="white")
                ]
            )
            open_dialog_safe(page, dlg)

    def open_penalty_dialog(e, w_id, w_name, abs_count, absent_dates, default_pen, total_penalty):
        pen_input = ft.TextField(
            label="Deduction per Absent Day (PKR)", 
            value=str(int(default_pen)), 
            keyboard_type=ft.KeyboardType.NUMBER, 
            border_color="blue", 
            border_radius=8, 
            autofocus=True
        )
        
        def save_penalty(e):
            try: 
                val = float(pen_input.value)
            except ValueError: 
                val = 0
            db.set_custom_deduction(w_id, val)
            dlg.open = False
            page.update()
            page.run_thread(load_monthly_tab)
            show_snack(page, "Deduction Saved", "green")
            
        pen_input.on_submit = save_penalty
        
        if not absent_dates:
            dates_ui = ft.Text("No absences.", italic=True, color="grey")
        else:
            date_controls = []
            for d in absent_dates:
                date_controls.append(ft.Text(f"• {d}", size=14, color="#EF4444", weight="bold"))
            dates_ui = ft.Column(date_controls, spacing=4, scroll=ft.ScrollMode.AUTO, height=120)

        def close_penalty(e):
            dlg.open = False
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Text(f"Absent Details: {w_name}", weight="bold"), 
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Total Absent Days: {abs_count}", color="red", weight="bold"), 
                    dates_ui, 
                    ft.Divider(height=10, color="transparent"), 
                    pen_input, 
                    ft.Text("Fridays auto-calculated.", size=11, color="grey"), 
                    ft.Container(
                        content=ft.Row([
                            ft.Text(f"Current Total Penalty: -{int(total_penalty)} PKR", color="white", weight="bold")
                        ], alignment=ft.MainAxisAlignment.CENTER), 
                        bgcolor="#EF4444", 
                        padding=10, 
                        border_radius=5
                    )
                ], tight=True), 
                width=350
            ), 
            actions=[
                ft.TextButton("Cancel", on_click=close_penalty), 
                ft.ElevatedButton("Apply Deduction", on_click=save_penalty, bgcolor="#2D5B7A", color="white")
            ]
        )
        open_dialog_safe(page, dlg)

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

    search_input = ft.TextField(
        label="Search Name or ID...", 
        width=250, 
        border_radius=8, 
        content_padding=12, 
        border_color="#D1D5DB", 
        bgcolor="#F9FAFB", 
        height=40, 
        prefix_icon=ft.Icons.SEARCH, 
        on_change=lambda e: load_monthly_tab()
    )

    def load_monthly_tab(e=None):
        new_list_controls = []
        start, end, lbl = get_period_range()
        start_sql = start.strftime("%Y-%m-%d")
        end_sql = end.strftime("%Y-%m-%d")
        month_label.value = lbl
        
        query = search_input.value.lower() if search_input.value else ""

        c = db.conn.cursor()
        
        c.execute("SELECT * FROM workers WHERE salary_type='Monthly'")
        workers = c.fetchall()
        
        c.execute("SELECT worker_id, date, amount_earned, status FROM attendance WHERE date BETWEEN ? AND ?", (start_sql, end_sql))
        all_att = {}
        for r in c.fetchall():
            all_att.setdefault(r[0], []).append((r[1], r[2], r[3]))
            
        c.execute("SELECT worker_id, amount, reason FROM advances WHERE date BETWEEN ? AND ?", (start_sql, end_sql))
        all_adv = {}
        for r in c.fetchall():
            all_adv.setdefault(r[0], []).append((r[1], r[2]))
            
        # ONLY Fetch Unpaid Overtime for final calculation
        c.execute("SELECT worker_id, SUM(amount) FROM overtime_history WHERE date BETWEEN ? AND ? AND (status='Unpaid' OR status IS NULL) GROUP BY worker_id", (start_sql, end_sql))
        all_unpaid_ot = {r[0]: r[1] for r in c.fetchall()}
        
        c.execute("SELECT worker_name FROM records WHERE period_start=? AND period_end=? AND salary_type='Monthly'", (start_sql, end_sql))
        paid_workers = {r[0] for r in c.fetchall()}
        
        c.execute("SELECT worker_id, deduction_amount FROM custom_deductions")
        all_custom_penalties = {r[0]: r[1] for r in c.fetchall()}

        header_row = ft.Row([
            ft.Text("ID", width=50, weight="bold", color=COLOR_TEXT_SUB, size=13), 
            ft.Text("Name", width=140, weight="bold", color=COLOR_TEXT_SUB, size=13), 
            ft.Text("Base", width=80, weight="bold", color=COLOR_TEXT_SUB, size=13), 
            ft.Text("Absents", width=120, weight="bold", color="#F59E0B", size=13), 
            ft.Text("Unpaid OT", width=95, weight="bold", color="#10B981", size=13),
            ft.Text("Prev Bal", width=95, weight="bold", color="#3B82F6", size=13), 
            ft.Text("Advances", width=85, weight="bold", color="#EF4444", size=13), 
            ft.Container(expand=True), 
            ft.Text("Final", width=110, weight="bold", color="#10B981", size=13), 
            ft.Text("Status", width=100, weight="bold", color=COLOR_TEXT_SUB, size=13, text_align=ft.TextAlign.CENTER)
        ])
        
        header_container = ft.Container(
            content=header_row,
            bgcolor=COLOR_BG_LIGHT, 
            padding=ft.padding.symmetric(vertical=10, horizontal=15), 
            border=ft.border.only(bottom=ft.border.BorderSide(2, COLOR_BORDER))
        )
        new_list_controls.append(header_container)
        
        visible_index = 0
        for w in workers:
            w_id = w[0]
            w_name = w[1]
            w_base = w[7]
            w_custom_id = w[8]
            display_id = f"M-{w_custom_id}"
            
            if query and query not in w_name.lower() and query not in display_id.lower(): 
                continue

            adv_list = all_adv.get(w_id, [])
            carry_forward = sum(float(a[0]) for a in adv_list if a[1] and "Carry Forward" in a[1])
            standard_adv = sum(float(a[0]) for a in adv_list if not a[1] or "Carry Forward" not in a[1])
            
            absent_count, absent_dates = calculate_absents_mem(w_id, start, end, all_att)
            custom_pen = all_custom_penalties.get(w_id)
            
            penalty_per_day = custom_pen if custom_pen is not None else int(w_base / 26)
            total_penalty = absent_count * penalty_per_day
            
            overtime_unpaid_amt = all_unpaid_ot.get(w_id, 0.0)
            
            final = (w_base - total_penalty) - carry_forward - standard_adv + overtime_unpaid_amt
            is_paid = w_name in paid_workers
            
            def make_status_click(wid, wname, final_amt, paid_status, ot_amt):
                return lambda e: handle_status_click(e, wname, start_sql, end_sql, paid_status, wid, final_amt, "Monthly", ot_amt)

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
                    ft.Text(f"{absent_count} D" + (f" (-{int(total_penalty):,})" if total_penalty > 0 else ""), color="#F59E0B", weight="bold", size=12)
                ], spacing=4), 
                on_click=lambda e, wid=w_id, wn=w_name, acount=absent_count, adates=absent_dates, dp=penalty_per_day, tp=total_penalty: open_penalty_dialog(e, wid, wn, acount, adates, dp, tp), 
                tooltip="Click to view dates", 
                ink=True, 
                width=120
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

            def make_hover(idx):
                def hover(e):
                    e.control.bgcolor = "#F1F5F9" if e.data == "true" else ("white" if idx % 2 == 0 else "#FAFAFA")
                    e.control.update()
                return hover

            worker_row = ft.Row([
                ft.Text(display_id, width=50, weight="w600", color=COLOR_TEXT_MAIN, size=13), 
                ft.Text(w_name, width=140, weight="bold", color=COLOR_TEXT_MAIN, size=15), 
                ft.Text(f"{int(w_base):,}", width=80, color=COLOR_TEXT_SUB, size=13), 
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
            
        monthly_grid.controls = new_list_controls
        page.update()
    
    def finalize_month(e):
        def background_finalize():
            start, end, _ = get_period_range()
            start_sql = start.strftime("%Y-%m-%d")
            end_sql = end.strftime("%Y-%m-%d")
            
            c = db.conn.cursor()
            
            c.execute("SELECT * FROM workers WHERE salary_type='Monthly'")
            workers = c.fetchall()
            
            c.execute("SELECT worker_id, date, amount_earned, status FROM attendance WHERE date BETWEEN ? AND ?", (start_sql, end_sql))
            all_att = {}
            for r in c.fetchall(): all_att.setdefault(r[0], []).append((r[1], r[2], r[3]))
            
            c.execute("SELECT worker_id, amount, reason FROM advances WHERE date BETWEEN ? AND ?", (start_sql, end_sql))
            all_adv = {}
            for r in c.fetchall(): all_adv.setdefault(r[0], []).append((r[1], r[2]))
            
            c.execute("SELECT worker_id, SUM(amount) FROM overtime_history WHERE date BETWEEN ? AND ? AND (status='Unpaid' OR status IS NULL) GROUP BY worker_id", (start_sql, end_sql))
            all_unpaid_ot = {r[0]: r[1] for r in c.fetchall()}
            
            c.execute("SELECT worker_name FROM records WHERE period_start=? AND period_end=? AND salary_type='Monthly'", (start_sql, end_sql))
            paid_workers = {r[0] for r in c.fetchall()}
            
            c.execute("SELECT worker_id, deduction_amount FROM custom_deductions")
            all_custom_penalties = {r[0]: r[1] for r in c.fetchall()}

            for w in workers:
                w_id = w[0]
                w_name = w[1]
                w_base = w[7]
                
                adv_list = all_adv.get(w_id, [])
                adv = sum(float(a[0]) for a in adv_list)
                
                absent_count, _ = calculate_absents_mem(w_id, start, end, all_att)
                custom_pen = all_custom_penalties.get(w_id)
                total_penalty = absent_count * (custom_pen if custom_pen is not None else int(w_base / 26))
                
                overtime_unpaid_amt = all_unpaid_ot.get(w_id, 0.0)
                
                final = (w_base - total_penalty) - adv + overtime_unpaid_amt
                
                is_paid = w_name in paid_workers
                
                if not is_paid: 
                    actual_paid = final if final > 0 else 0
                    db.save_record(start_sql, end_sql, w_name, "Monthly", actual_paid)
                    diff = final - actual_paid
                    
                    if diff != 0:
                        curr_start = datetime.strptime(start_sql, "%Y-%m-%d")
                        next_month_start = (curr_start.replace(day=28) + timedelta(days=4)).replace(day=1)
                        reason = "Previous Balance Carry Forward" if diff > 0 else "Overpayment Carry Forward"
                        db.add_advance(w_id, -diff, reason, next_month_start.strftime("%Y-%m-%d"))
                        
                    if overtime_unpaid_amt > 0:
                        c.execute("UPDATE overtime_history SET status='Paid' WHERE worker_id=? AND date BETWEEN ? AND ? AND (status='Unpaid' OR status IS NULL)", (w_id, start_sql, end_sql))
                        db.conn.commit()
                        
            show_snack(page, "Successfully Saved!", "green")
            load_monthly_tab()
            
        page.run_thread(background_finalize)

    top_row = ft.Row([
        ft.Text("Monthly View", size=22, weight="bold", color=COLOR_TEXT_MAIN), 
        ft.Row([
            ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=change_period_left), 
            month_clickable, 
            ft.IconButton(icon=ft.Icons.ARROW_FORWARD, on_click=change_period_right), 
            ft.TextButton("This Month", icon=ft.Icons.TODAY, on_click=reset_to_today, style=ft.ButtonStyle(color=COLOR_PRIMARY))
        ], alignment=ft.MainAxisAlignment.CENTER), 
        ft.Row([
            search_input, 
            ft.FilledButton("Finalize All", icon=ft.Icons.SAVE, on_click=finalize_month, bgcolor="#111827")
        ], spacing=10)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    grid_container = ft.Container(
        content=monthly_grid, 
        expand=True, 
        bgcolor="white", 
        border_radius=8, 
        border=ft.border.all(1, COLOR_BORDER), 
        shadow=ft.BoxShadow(spread_radius=1, blur_radius=2, color="#0D000000", offset=ft.Offset(0, 1)), 
        clip_behavior=ft.ClipBehavior.HARD_EDGE
    )

    monthly_container = ft.Container(
        content=ft.Column([
            top_row, 
            ft.Divider(height=5, color="transparent"), 
            grid_container
        ], expand=True), 
        visible=False
    )

    return monthly_container, load_monthly_tab