import flet as ft
from datetime import datetime, timedelta

def get_overtime_view(page: ft.Page, db, state, show_snack, open_dialog_safe):
    COLOR_TEXT_MAIN = "#111827"
    COLOR_TEXT_SUB = "#4B5563"
    COLOR_BORDER = "#E5E7EB"
    COLOR_BG_LIGHT = "#F3F4F6"
    COLOR_PRIMARY = "#0284C7"
    
    ot_grid = ft.ListView(spacing=0, expand=True)
    date_label = ft.Text("", size=16, weight="bold")
    stats_container = ft.Container()
    
    filter_state = {"mode": "All"}

    # --- DATABASE MIGRATION SAFEY CHECK ---
    try:
        c = db.conn.cursor()
        c.execute("SELECT status FROM overtime_history LIMIT 1")
    except:
        c = db.conn.cursor()
        c.execute("ALTER TABLE overtime_history ADD COLUMN status TEXT DEFAULT 'Unpaid'")
        db.conn.commit()

    if "ot_view_mode" not in state:
        state["ot_view_mode"] = "Specific Date"
        state["ot_view_date"] = datetime.now()
        state["ot_start"] = datetime.now() - timedelta(days=7)
        state["ot_end"] = datetime.now()

    def get_week_bounds(ref_date):
        days_to_subtract = (ref_date.weekday() - 5) % 7
        start = ref_date - timedelta(days=days_to_subtract)
        end = start + timedelta(days=5) 
        return start, end

    def get_ot_period_range():
        mode = state["ot_view_mode"]
        ref_date = state["ot_view_date"]
        
        if mode == "Specific Date":
            return ref_date, ref_date, ref_date.strftime("%d %b %Y")
            
        elif mode == "Week":
            start, end = get_week_bounds(ref_date)
            return start, end, f"{start.strftime('%d %b')} - {end.strftime('%d %b %Y')} (Week)"
            
        elif mode == "Month":
            start = ref_date.replace(day=1)
            next_m = start.replace(day=28) + timedelta(days=4)
            end = next_m - timedelta(days=next_m.day)
            return start, end, start.strftime("%B %Y")
            
        elif mode == "Date Range":
            return state["ot_start"], state["ot_end"], f"{state['ot_start'].strftime('%d %b %Y')} - {state['ot_end'].strftime('%d %b %Y')}"

    # --- FILTER DIALOG LOGIC ---
    safe_first = datetime(2000, 1, 1)
    safe_last = datetime(2035, 12, 31)
    spec_in = ft.TextField(read_only=True, width=150, height=40, content_padding=10, text_align=ft.TextAlign.CENTER)
    start_in = ft.TextField(read_only=True, width=130, height=40, content_padding=10, text_align=ft.TextAlign.CENTER)
    end_in = ft.TextField(read_only=True, width=130, height=40, content_padding=10, text_align=ft.TextAlign.CENTER)

    def handle_spec_change(e):
        if e.control.value:
            spec_in.value = e.control.value.strftime('%Y-%m-%d')
            page.update()

    def handle_start_change(e):
        if e.control.value:
            start_in.value = e.control.value.strftime('%Y-%m-%d')
            page.update()

    def handle_end_change(e):
        if e.control.value:
            end_in.value = e.control.value.strftime('%Y-%m-%d')
            page.update()

    dp_spec = ft.DatePicker(first_date=safe_first, last_date=safe_last, on_change=handle_spec_change)
    dp_start = ft.DatePicker(first_date=safe_first, last_date=safe_last, on_change=handle_start_change)
    dp_end = ft.DatePicker(first_date=safe_first, last_date=safe_last, on_change=handle_end_change)

    def open_filter_dialog(e):
        if dp_spec not in page.overlay:
            page.overlay.extend([dp_spec, dp_start, dp_end])
            
        current_mode = [state["ot_view_mode"]]
        chips_row = ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=10)
        dynamic_content = ft.Container()

        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        month_dd = ft.Dropdown(options=[ft.dropdown.Option(m) for m in months], value=state["ot_view_date"].strftime("%B"), width=145, border_radius=8)
        year_dd = ft.Dropdown(options=[ft.dropdown.Option(str(y)) for y in range(2020, 2035)], value=state["ot_view_date"].strftime("%Y"), width=145, border_radius=8)
        month_row = ft.Row([month_dd, year_dd], alignment=ft.MainAxisAlignment.CENTER)

        spec_in.value = state["ot_view_date"].strftime("%Y-%m-%d")
        
        def open_dp_spec_dialog(e):
            dp_spec.value = datetime.strptime(spec_in.value, "%Y-%m-%d")
            dp_spec.open = True
            page.update()

        spec_row = ft.Row([
            spec_in,
            ft.IconButton(ft.Icons.CALENDAR_MONTH, icon_color=COLOR_PRIMARY, on_click=open_dp_spec_dialog)
        ], alignment=ft.MainAxisAlignment.CENTER)

        weeks_col = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, height=180)
        
        def render_week_items():
            weeks_col.controls.clear()
            sel_month_idx = months.index(month_dd_w.value) + 1
            sel_year = int(year_dd_w.value)
            first_day = datetime(sel_year, sel_month_idx, 1)
            
            days_to_subtract = (first_day.weekday() - 5) % 7
            curr_start = first_day - timedelta(days=days_to_subtract)
            active_start, _ = get_week_bounds(state["ot_view_date"])
            
            week_num = 1
            while True:
                curr_end = curr_start + timedelta(days=5)
                if curr_start.month != sel_month_idx and curr_start > first_day:
                    break
                    
                is_active = (curr_start.date() == active_start.date() and current_mode[0] == "Week")
                
                def make_select_handler(st_date):
                    return lambda e: assign_week_and_close(st_date)

                weeks_col.controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.DATE_RANGE, color="white" if is_active else COLOR_PRIMARY, size=18),
                            ft.Text(f"Week {week_num}: {curr_start.strftime('%d %b')} to {curr_end.strftime('%d %b %Y')}", weight="bold", color="white" if is_active else COLOR_TEXT_MAIN, size=13)
                        ]),
                        padding=ft.padding.symmetric(vertical=10, horizontal=12),
                        bgcolor=COLOR_PRIMARY if is_active else COLOR_BG_LIGHT,
                        border_radius=8, ink=True, on_click=make_select_handler(curr_start)
                    )
                )
                curr_start += timedelta(days=7)
                week_num += 1
            page.update()

        def assign_week_and_close(st_date):
            state["ot_view_mode"] = "Week"
            state["ot_view_date"] = st_date
            filter_dialog.open = False
            page.update()
            load_overtime_ui()

        def trigger_week_rebuild(e):
            render_week_items()

        month_dd_w = ft.Dropdown(options=[ft.dropdown.Option(m) for m in months], value=state["ot_view_date"].strftime("%B"), width=145, border_radius=8)
        year_dd_w = ft.Dropdown(options=[ft.dropdown.Option(str(y)) for y in range(2020, 2035)], value=state["ot_view_date"].strftime("%Y"), width=105, border_radius=8)
        
        month_dd_w.on_change = trigger_week_rebuild
        year_dd_w.on_change = trigger_week_rebuild
        
        week_picker_row = ft.Column([
            ft.Row([month_dd_w, year_dd_w], alignment=ft.MainAxisAlignment.CENTER),
            ft.Divider(height=5, color="transparent"),
            weeks_col
        ], tight=True)

        start_in.value = state["ot_start"].strftime("%Y-%m-%d")
        end_in.value = state["ot_end"].strftime("%Y-%m-%d")
        
        def open_dp_start_dialog(e):
            dp_start.value = datetime.strptime(start_in.value, "%Y-%m-%d")
            dp_start.open = True
            page.update()
            
        def open_dp_end_dialog(e):
            dp_end.value = datetime.strptime(end_in.value, "%Y-%m-%d")
            dp_end.open = True
            page.update()

        range_row = ft.Column([
            ft.Row([ft.Text("Start:", width=40, weight="bold", color=COLOR_TEXT_SUB), start_in, ft.IconButton(ft.Icons.CALENDAR_MONTH, icon_color=COLOR_PRIMARY, on_click=open_dp_start_dialog)], alignment=ft.MainAxisAlignment.CENTER),
            ft.Row([ft.Text("End:", width=40, weight="bold", color=COLOR_TEXT_SUB), end_in, ft.IconButton(ft.Icons.CALENDAR_MONTH, icon_color=COLOR_PRIMARY, on_click=open_dp_end_dialog)], alignment=ft.MainAxisAlignment.CENTER)
        ], spacing=5)

        def update_dialog_ui():
            chips_row.controls.clear()
            modes = ["Specific Date", "Week", "Month", "Date Range"]
            for m in modes:
                is_active = (current_mode[0] == m)
                
                def set_mode(e, selected=m):
                    current_mode[0] = selected
                    update_dialog_ui()
                    page.update()

                chip = ft.Container(
                    content=ft.Text(m, color="white" if is_active else COLOR_TEXT_SUB, weight="bold", size=11),
                    bgcolor=COLOR_PRIMARY if is_active else COLOR_BG_LIGHT,
                    padding=ft.padding.symmetric(horizontal=10, vertical=8),
                    border_radius=8,
                    ink=True,
                    on_click=set_mode
                )
                chips_row.controls.append(chip)

            month_row.visible = (current_mode[0] == "Month")
            spec_row.visible = (current_mode[0] == "Specific Date")
            week_picker_row.visible = (current_mode[0] == "Week")
            range_row.visible = (current_mode[0] == "Date Range")
            dynamic_content.content = ft.Column([month_row, spec_row, week_picker_row, range_row], tight=True, alignment=ft.MainAxisAlignment.CENTER)
            if current_mode[0] == "Week":
                render_week_items()

        update_dialog_ui()

        def apply_filter(e):
            state["ot_view_mode"] = current_mode[0]
            
            if current_mode[0] == "Month":
                selected_month_idx = months.index(month_dd.value) + 1
                selected_year = int(year_dd.value)
                state["ot_view_date"] = datetime(selected_year, selected_month_idx, 1)
            elif current_mode[0] == "Specific Date":
                state["ot_view_date"] = datetime.strptime(spec_in.value, "%Y-%m-%d")
            elif current_mode[0] == "Date Range":
                state["ot_start"] = datetime.strptime(start_in.value, "%Y-%m-%d")
                state["ot_end"] = datetime.strptime(end_in.value, "%Y-%m-%d")

            filter_dialog.open = False
            page.update()
            load_overtime_ui()

        def close_filter(e):
            filter_dialog.open = False
            page.update()

        filter_dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.Icons.FILTER_ALT, color=COLOR_PRIMARY),
                ft.Text("Select Period", weight="bold", size=18)
            ]),
            content=ft.Container(
                content=ft.Column([
                    chips_row,
                    ft.Divider(height=10, color="transparent"),
                    dynamic_content
                ], tight=True),
                width=450,
                padding=10
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_filter),
                ft.ElevatedButton("Apply Filter", bgcolor=COLOR_PRIMARY, color="white", on_click=apply_filter)
            ],
            shape=ft.RoundedRectangleBorder(radius=12)
        )
        open_dialog_safe(page, filter_dialog)

    period_clickable = ft.Container(
        content=date_label, 
        on_click=open_filter_dialog, 
        ink=True, 
        padding=ft.padding.symmetric(horizontal=10, vertical=5), 
        border_radius=5, 
        tooltip="Click to Change View Filter"
    )

    def change_period(direction=0):
        mode = state["ot_view_mode"]
        if mode == "Specific Date":
            state["ot_view_date"] += timedelta(days=direction)
        elif mode == "Week":
            state["ot_view_date"] += timedelta(weeks=direction)
        elif mode == "Month":
            curr = state["ot_view_date"]
            new_m = curr.month + direction
            y_adj = 0
            if new_m > 12: 
                new_m = 1
                y_adj = 1
            elif new_m < 1: 
                new_m = 12
                y_adj = -1
            state["ot_view_date"] = curr.replace(month=new_m, year=curr.year + y_adj)
        elif mode == "Date Range":
            delta = (state["ot_end"] - state["ot_start"]).days + 1
            state["ot_start"] += timedelta(days=direction * delta)
            state["ot_end"] += timedelta(days=direction * delta)
            
        load_overtime_ui()

    def reset_to_today(e):
        state["ot_view_mode"] = "Specific Date"
        state["ot_view_date"] = datetime.now()
        load_overtime_ui()
        page.update()

    search_input = ft.TextField(
        label="Search Name or ID...", 
        width=250, 
        border_radius=8, 
        content_padding=12, 
        border_color="#D1D5DB", 
        bgcolor="#F9FAFB", 
        height=40, 
        prefix_icon=ft.Icons.SEARCH, 
        on_change=lambda e: load_overtime_ui()
    )

    rate_val = db.get_setting("global_overtime_rate", "150")
    rate_input = ft.TextField(
        value=rate_val, 
        label="Global Hourly Rate (PKR)", 
        width=180, 
        border_radius=8, 
        content_padding=12, 
        border_color="#D1D5DB", 
        bgcolor="#F9FAFB", 
        height=40, 
        prefix_icon=ft.Icons.MONETIZATION_ON,
        keyboard_type=ft.KeyboardType.NUMBER
    )
    
    def save_global_rate(e):
        try:
            val = float(rate_input.value)
            db.set_setting("global_overtime_rate", str(val))
            show_snack(page, "Global Overtime Rate Saved!", "green")
        except:
            show_snack(page, "Invalid Rate", "red")
            
    rate_input.on_submit = save_global_rate
    rate_input.on_blur = save_global_rate

    # --- ADD OVERTIME MANUAL DIALOG ---
    def open_add_ot_dialog(e, worker_id, w_name):
        current_rate = float(db.get_setting("global_overtime_rate", "150"))
        
        hours_input = ft.TextField(label="Working Hours", value="1.0", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8)
        amount_input = ft.TextField(label="Calculated Amount (PKR)", value=str(int(current_rate)), border_color="blue", border_radius=8)
        
        def on_hours_change(e):
            try:
                hrs = float(hours_input.value)
                amount_input.value = str(int(hrs * current_rate))
                page.update()
            except ValueError:
                pass
                
        hours_input.on_change = on_hours_change
        
        def save_manual_ot(e):
            try:
                final_amt = float(amount_input.value)
                final_hours = float(hours_input.value)
                # Save it to the current selected view date (or today if range)
                save_date = state["ot_view_date"].strftime("%Y-%m-%d") if state["ot_view_mode"] != "Date Range" else state["ot_end"].strftime("%Y-%m-%d")
                
                c = db.conn.cursor()
                c.execute("INSERT INTO overtime_history (worker_id, date, amount, hours, status) VALUES (?, ?, ?, ?, 'Unpaid')", (worker_id, save_date, final_amt, final_hours))
                db.conn.commit()
                
                dlg.open = False
                page.update()
                load_overtime_ui()
                show_snack(page, f"Added {final_hours} hrs OT for {w_name}!", "green")
            except ValueError:
                show_snack(page, "Invalid number entered.", "red")

        amount_input.on_submit = save_manual_ot
        hours_input.on_submit = save_manual_ot

        def close_dialog(e):
            dlg.open = False
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Text(f"Add Overtime: {w_name}", weight="bold"),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Rate: {int(current_rate)} PKR/hr. You can edit the final amount directly.", color="grey", size=12),
                    ft.Divider(height=10, color="transparent"),
                    hours_input,
                    amount_input,
                ], tight=True), width=350
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog), 
                ft.ElevatedButton("Save Overtime", on_click=save_manual_ot, bgcolor="#0284C7", color="white")
            ]
        )
        open_dialog_safe(page, dlg)

    # --- PAY OVERTIME DIALOG ---
    def open_pay_ot_dialog(e, worker_id, w_name, total_unpaid, start_sql, end_sql):
        pay_amount_input = ft.TextField(label="Amount to Pay (PKR)", value=str(int(total_unpaid)), border_color="green", border_radius=8, autofocus=True)
        
        def process_payment(e):
            try:
                actual_paid = float(pay_amount_input.value)
                diff = total_unpaid - actual_paid
                
                c = db.conn.cursor()
                # Mark existing as paid
                c.execute("UPDATE overtime_history SET status='Paid' WHERE worker_id=? AND date BETWEEN ? AND ? AND (status='Unpaid' OR status IS NULL)", (worker_id, start_sql, end_sql))
                
                # If they didn't pay exactly the total unpaid, save the remaining as carry forward
                if diff != 0:
                    today_str = datetime.now().strftime("%Y-%m-%d")
                    c.execute("INSERT INTO overtime_history (worker_id, date, amount, hours, status) VALUES (?, ?, ?, 0, 'Unpaid')", (worker_id, today_str, diff))
                
                db.conn.commit()
                
                dlg.open = False
                page.update()
                load_overtime_ui()
                show_snack(page, f"Overtime paid for {w_name}!", "green")
                
            except ValueError:
                show_snack(page, "Invalid payment amount.", "red")

        pay_amount_input.on_submit = process_payment

        def close_dialog(e):
            dlg.open = False
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Text(f"Pay Overtime: {w_name}", weight="bold"),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(f"Total Unpaid in period: {int(total_unpaid)} PKR", weight="bold"),
                    ft.Text("Any unpaid difference will be carried forward automatically.", color="grey", size=12),
                    ft.Divider(height=10, color="transparent"),
                    pay_amount_input,
                ], tight=True), width=350
            ),
            actions=[
                ft.TextButton("Cancel", on_click=close_dialog), 
                ft.ElevatedButton("Mark Paid", on_click=process_payment, bgcolor="#10B981", color="white")
            ]
        )
        open_dialog_safe(page, dlg)

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
            expand=True, bgcolor=bg_color, padding=15, border_radius=8, border=ft.border.all(border_width, border_color),
            shadow=ft.BoxShadow(spread_radius=1, blur_radius=2, color="#0A000000", offset=ft.Offset(0, 1)),
            on_click=on_click_action, ink=True, tooltip="Click to filter workers"
        )

    def set_filter(mode):
        if filter_state["mode"] == mode:
            filter_state["mode"] = "All"
        else:
            filter_state["mode"] = mode
        page.run_thread(load_overtime_ui)

    def load_overtime_ui(e=None):
        new_list_controls = []
        
        start_date, end_date, lbl = get_ot_period_range()
        start_sql = start_date.strftime("%Y-%m-%d")
        end_sql = end_date.strftime("%Y-%m-%d")
        date_label.value = lbl
        
        workers = db.get_workers()
        query = search_input.value.lower() if search_input.value else ""

        visible_index = 0
        total_unpaid_period = 0
        total_paid_period = 0
        participating_count = 0
        
        c = db.conn.cursor()
        
        # Fetch Unpaid (Amounts and Hours)
        c.execute("SELECT worker_id, SUM(amount), SUM(hours) FROM overtime_history WHERE date BETWEEN ? AND ? AND (status='Unpaid' OR status IS NULL) GROUP BY worker_id", (start_sql, end_sql))
        unpaid_data = {row[0]: (row[1] or 0.0, row[2] or 0.0) for row in c.fetchall()}
        
        # Fetch Paid (Amounts and Hours)
        c.execute("SELECT worker_id, SUM(amount), SUM(hours) FROM overtime_history WHERE date BETWEEN ? AND ? AND status='Paid' GROUP BY worker_id", (start_sql, end_sql))
        paid_data = {row[0]: (row[1] or 0.0, row[2] or 0.0) for row in c.fetchall()}
        
        for w in workers:
            w_id = w[0]
            w_name = w[1]
            w_type = w[6]
            w_custom_id = w[8]
            display_id = f"W-{w_custom_id}" if w_type == "Weekly" else f"M-{w_custom_id}"
            
            # Base text search condition
            matches_search = True
            if query and query not in w_name.lower() and query not in display_id.lower():
                matches_search = False
            
            unpaid_amt, unpaid_hrs = unpaid_data.get(w_id, (0.0, 0.0))
            paid_amt, paid_hrs = paid_data.get(w_id, (0.0, 0.0))
            total_hrs = unpaid_hrs + paid_hrs
            
            # Accumulate totals ONLY if they match the search query (ignoring box filter)
            if matches_search:
                total_unpaid_period += unpaid_amt
                total_paid_period += paid_amt
                
                if unpaid_amt > 0 or paid_amt > 0 or total_hrs > 0:
                    participating_count += 1
            
            # Now enforce BOTH the search filter and the card click filter for the list
            if not matches_search:
                continue
                
            if filter_state["mode"] == "Participating" and (unpaid_amt == 0 and paid_amt == 0 and total_hrs == 0):
                continue
            if filter_state["mode"] == "Unpaid" and unpaid_amt == 0:
                continue
            if filter_state["mode"] == "Paid" and paid_amt == 0:
                continue

            unpaid_ui = ft.Text(f"{int(unpaid_amt):,} PKR", width=110, weight="bold", color="#F59E0B" if unpaid_amt > 0 else "grey", size=14)
            paid_ui = ft.Text(f"{int(paid_amt):,} PKR", width=110, weight="bold", color="#10B981" if paid_amt > 0 else "grey", size=14)
            hrs_ui = ft.Text(f"{total_hrs:g} h", width=70, weight="bold", color=COLOR_TEXT_MAIN, size=13)
            
            # Use dynamic sizing with nice padding to prevent text squishing
            add_btn = ft.ElevatedButton(
                "Add OT", 
                icon=ft.Icons.ADD, 
                bgcolor="#0284C7", 
                color="white", 
                height=35, 
                style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=16, vertical=0)),
                on_click=lambda e, wid=w_id, wn=w_name: open_add_ot_dialog(e, wid, wn)
            )
            
            pay_btn = ft.ElevatedButton(
                "Pay OT", 
                icon=ft.Icons.PAYMENTS, 
                bgcolor="#10B981" if unpaid_amt > 0 else "#E5E7EB", 
                color="white" if unpaid_amt > 0 else "grey", 
                height=35, 
                disabled=(unpaid_amt <= 0), 
                style=ft.ButtonStyle(padding=ft.padding.symmetric(horizontal=16, vertical=0)),
                on_click=lambda e, wid=w_id, wn=w_name, unp=unpaid_amt: open_pay_ot_dialog(e, wid, wn, unp, start_sql, end_sql)
            )

            action_row = ft.Row([add_btn, pay_btn], spacing=8, alignment=ft.MainAxisAlignment.END, width=250)

            def make_hover(idx):
                def hover(e):
                    e.control.bgcolor = "#F1F5F9" if e.data == "true" else ("white" if idx % 2 == 0 else "#FAFAFA")
                    e.control.update() 
                return hover

            new_list_controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(display_id, width=60, weight="w600", color=COLOR_TEXT_MAIN, size=13),
                        ft.Text(w_name, width=170, weight="bold", color=COLOR_TEXT_MAIN, size=15),
                        ft.Text(w_type, width=80, color=COLOR_TEXT_SUB, size=13),
                        hrs_ui,
                        unpaid_ui,
                        paid_ui,
                        ft.Container(expand=True), 
                        action_row
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.padding.symmetric(vertical=8, horizontal=15), 
                    bgcolor="white" if visible_index % 2 == 0 else "#FAFAFA", 
                    border=ft.border.only(bottom=ft.border.BorderSide(1, COLOR_BORDER)),
                    on_hover=make_hover(visible_index)
                )
            )
            visible_index += 1

        stats_container.content = ft.Row([
            create_stat_card("Participating", participating_count, ft.Icons.PEOPLE, "#3B82F6", lambda e: set_filter("Participating"), filter_state["mode"] == "Participating"),
            create_stat_card("Unpaid Overtime", f"{int(total_unpaid_period):,} PKR", ft.Icons.PENDING_ACTIONS, "#F59E0B", lambda e: set_filter("Unpaid"), filter_state["mode"] == "Unpaid"),
            create_stat_card("Paid Overtime", f"{int(total_paid_period):,} PKR", ft.Icons.CHECK_CIRCLE, "#10B981", lambda e: set_filter("Paid"), filter_state["mode"] == "Paid")
        ], spacing=15)
        
        # We append the header *after* so we don't clear it
        final_ui_controls = []
        final_ui_controls.append(
            ft.Container(
                content=ft.Row([
                    ft.Text("ID", width=60, weight="bold", color=COLOR_TEXT_SUB, size=13),
                    ft.Text("Name", width=170, weight="bold", color=COLOR_TEXT_SUB, size=13),
                    ft.Text("Type", width=80, weight="bold", color=COLOR_TEXT_SUB, size=13),
                    ft.Text("Hours", width=70, weight="bold", color=COLOR_PRIMARY, size=13),
                    ft.Text("Unpaid OT", width=110, weight="bold", color="#F59E0B", size=13),
                    ft.Text("Paid OT", width=110, weight="bold", color="#10B981", size=13),
                    ft.Container(expand=True),
                    ft.Text("Action", width=250, weight="bold", color=COLOR_TEXT_SUB, size=13, text_align=ft.TextAlign.CENTER),
                ]),
                bgcolor=COLOR_BG_LIGHT, padding=ft.padding.symmetric(vertical=10, horizontal=15), border=ft.border.only(bottom=ft.border.BorderSide(2, COLOR_BORDER))
            )
        )
        final_ui_controls.extend(new_list_controls)
        
        ot_grid.controls = final_ui_controls
        
        try:
            stats_container.update()
            ot_grid.update()
        except:
            pass

        page.update()

    main_view = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Manual Overtime Management", size=22, weight="bold", color=COLOR_TEXT_MAIN),
                ft.Row([
                    ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, on_click=lambda e: change_period(-1)),
                    period_clickable,
                    ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, on_click=lambda e: change_period(1)),
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Row([
                    rate_input, 
                    search_input, 
                    ft.FilledButton("Today", icon=ft.Icons.TODAY, on_click=reset_to_today, bgcolor="#0284C7")
                ], spacing=10)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=5, color="transparent"),
            stats_container,
            ft.Divider(height=5, color="transparent"),
            ft.Container(
                content=ot_grid, 
                expand=True, 
                bgcolor="white", 
                border_radius=8, 
                border=ft.border.all(1, COLOR_BORDER), 
                shadow=ft.BoxShadow(spread_radius=1, blur_radius=2, color="#0D000000", offset=ft.Offset(0, 1)), 
                clip_behavior=ft.ClipBehavior.HARD_EDGE
            )
        ], expand=True),
        visible=False
    )

    return main_view, load_overtime_ui