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

    try:
        c = db.conn.cursor()
        c.execute("SELECT shift FROM overtime_history LIMIT 1")
    except:
        c = db.conn.cursor()
        c.execute("ALTER TABLE overtime_history ADD COLUMN shift TEXT DEFAULT 'Morning'")
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
                        padding=ft.Padding.symmetric(vertical=10, horizontal=12),
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
                    padding=ft.Padding.symmetric(horizontal=10, vertical=8),
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
        padding=ft.Padding.symmetric(horizontal=10, vertical=5), 
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
        width=250, 
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


    # --- DYNAMIC ADD OVERTIME MANUAL DIALOG ---
    def open_add_ot_dialog(e=None, prefill_worker_id=None, prefill_worker_name=None):
        current_rate = float(db.get_setting("global_overtime_rate", "150"))
        state_worker = {"id": prefill_worker_id, "name": prefill_worker_name}
        
        dlg = ft.AlertDialog(shape=ft.RoundedRectangleBorder(radius=12))
        dialog_view = ft.Container(width=380)

        # --- Form Elements ---
        worker_icon = ft.Icon(ft.Icons.CHECK_CIRCLE if prefill_worker_id else ft.Icons.SEARCH, color="#10B981" if prefill_worker_id else "#6B7280")
        worker_label = ft.Text(prefill_worker_name if prefill_worker_name else "Click to Search & Select Worker...", color="#065F46" if prefill_worker_id else "#6B7280", weight="bold" if prefill_worker_id else "normal")
        
        def show_picker(e):
            show_picker_view(True)
            
        worker_selector = ft.Container(
            content=ft.Row([worker_icon, worker_label]), 
            on_click=show_picker, 
            bgcolor="#D1FAE5" if prefill_worker_id else "#F9FAFB", 
            border=ft.border.all(1, "#10B981" if prefill_worker_id else "#D1D5DB"), 
            border_radius=8, padding=12, height=50, ink=True
        )
        
        default_date = state["ot_view_date"].strftime("%Y-%m-%d") if state["ot_view_mode"] != "Date Range" else state["ot_end"].strftime("%Y-%m-%d")
        date_input = ft.TextField(label="Date", value=default_date, prefix_icon=ft.Icons.CALENDAR_TODAY, border_radius=8, border_color="#D1D5DB", bgcolor="#F9FAFB")
        
        hours_input = ft.TextField(label="Working Hours", value="1.0", keyboard_type=ft.KeyboardType.NUMBER, border_radius=8, autofocus=True if prefill_worker_id else False)
        amount_input = ft.TextField(label="Calculated Amount (PKR)", value=str(int(current_rate)), border_color="blue", border_radius=8)
        
        shift_dropdown = ft.Dropdown(
            label="OT Shift Type", options=[ft.dropdown.Option("Morning"), ft.dropdown.Option("Evening")], value="Morning", border_radius=8
        )
        
        def on_hours_change(e):
            try: amount_input.value = str(int(float(hours_input.value) * current_rate)); page.update()
            except ValueError: pass
                
        hours_input.on_change = on_hours_change
        
        def close_dialog(e):
            dlg.open = False; page.update()
            
        def save_manual_ot(e=None):
            if not state_worker["id"]:
                show_snack(page, "Please search and select a worker first.", "red")
                return
            try:
                final_amt = float(amount_input.value)
                final_hours = float(hours_input.value)
                c = db.conn.cursor()
                c.execute("INSERT INTO overtime_history (worker_id, date, amount, hours, status, shift) VALUES (?, ?, ?, ?, 'Unpaid', ?)", (state_worker["id"], date_input.value, final_amt, final_hours, shift_dropdown.value))
                db.conn.commit()
                dlg.open = False
                page.update()
                load_overtime_ui()
                show_snack(page, f"Added {final_hours} hrs OT for {state_worker['name']}!", "green")
            except ValueError:
                show_snack(page, "Invalid number entered.", "red")

        date_input.on_submit = save_manual_ot
        amount_input.on_submit = save_manual_ot
        hours_input.on_submit = save_manual_ot

        def show_form_view(do_update=False):
            dlg.title = ft.Row([ft.Icon(ft.Icons.MORE_TIME, color=COLOR_PRIMARY), ft.Text("Record Overtime", color=COLOR_PRIMARY, weight="bold")])
            dialog_view.content = ft.Column([
                worker_selector, ft.Divider(height=5, color="transparent"),
                date_input, shift_dropdown, hours_input, amount_input,
                ft.Text(f"Rate: {int(current_rate)} PKR/hr. You can edit the final amount directly.", color="grey", size=11),
            ], tight=True)
            dlg.actions = [ft.TextButton("Cancel", on_click=close_dialog), ft.ElevatedButton("Save Overtime", on_click=save_manual_ot, bgcolor="#0284C7", color="white")]
            if do_update: page.update()

        # --- Picker View ---
        workers = db.get_workers()
        search_input_picker = ft.TextField(label="Type Worker Name or ID...", autofocus=True, border_radius=8, height=50)
        list_view = ft.ListView(spacing=0, height=300)
        
        def filter_list(e=None):
            q = search_input_picker.value.lower() if search_input_picker.value else ""
            list_view.controls.clear()
            for w in workers:
                w_id = w[0]; w_name = w[1]; w_type = w[6]
                w_custom_id = w[8] if len(w) > 8 else w_id
                display_id = f"W-{w_custom_id}" if w_type == "Weekly" else f"M-{w_custom_id}"
                
                if q in w_name.lower() or q in w_type.lower() or q in str(w_id) or q in display_id.lower():
                    row = ft.Container(
                        content=ft.Row([
                            ft.Text(f"{display_id}  •  {w_name}", weight="bold", size=16, color="#111827"),
                            ft.Container(content=ft.Text(w_type.upper(), size=10, weight="bold", color="#0284C7"), bgcolor="#E0F2FE", padding=ft.Padding.symmetric(horizontal=6, vertical=2), border_radius=4)
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                        padding=15, bgcolor="white", border=ft.border.only(bottom=ft.border.BorderSide(1, "#E5E7EB")), ink=True, 
                        on_click=lambda e, wid=w_id, wname=w_name: handle_select(wid, wname)
                    )
                    list_view.controls.append(row)
            if e: page.update()

        search_input_picker.on_change = filter_list

        def handle_select(wid, wname):
            state_worker["id"] = wid
            state_worker["name"] = wname
            worker_label.value = wname
            worker_label.color = "#065F46"
            worker_label.weight = "bold"
            worker_selector.bgcolor = "#D1FAE5"
            worker_selector.border = ft.border.all(1, "#10B981")
            worker_icon.name = ft.Icons.CHECK_CIRCLE
            worker_icon.color = "#10B981"
            show_form_view(True)

        def show_picker_view(do_update=False):
            filter_list()
            dlg.title = ft.Text("🔍 Search & Select Worker", weight="bold", size=18)
            dialog_view.content = ft.Column([search_input_picker, ft.Divider(height=10, color="transparent"), list_view], tight=True)
            dlg.actions = [ft.TextButton("Back to Form", on_click=lambda e: show_form_view(True))]
            if do_update: page.update()

        show_form_view()
        dlg.content = dialog_view
        open_dialog_safe(page, dlg)


    # --- SHARED TABLE BUILDER FOR PROFESSIONAL DIALOGS ---
    def build_detail_table(rows):
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
                shift_disp = "Payment"
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

    # --- MONEY DETAILS DIALOGS ---
    def open_unpaid_ot_dialog(e, w_id, w_name, start_date, end_date):
        c = db.conn.cursor()
        c.execute("SELECT date, hours, amount, shift FROM overtime_history WHERE worker_id=? AND date BETWEEN ? AND ? AND (status='Unpaid' OR status IS NULL) ORDER BY date", (w_id, start_date, end_date))
        rows = c.fetchall()
        list_items = build_detail_table(rows)
            
        dlg = ft.AlertDialog(
            title=ft.Text(f"Unpaid OT Details: {w_name}", weight="bold", size=16),
            content=ft.Container(content=ft.Column(list_items, scroll=ft.ScrollMode.AUTO, tight=True), width=450),
            actions=[ft.TextButton("Close", on_click=lambda e: setattr(dlg, 'open', False) or page.update())]
        )
        open_dialog_safe(page, dlg)
        
    def open_paid_ot_dialog(e, w_id, w_name, start_date, end_date):
        c = db.conn.cursor()
        c.execute("SELECT date, hours, amount, shift FROM overtime_history WHERE worker_id=? AND date BETWEEN ? AND ? AND status='Paid' ORDER BY date", (w_id, start_date, end_date))
        rows = c.fetchall()
        list_items = build_detail_table(rows)
            
        dlg = ft.AlertDialog(
            title=ft.Text(f"Paid OT Details: {w_name}", weight="bold", size=16),
            content=ft.Container(content=ft.Column(list_items, scroll=ft.ScrollMode.AUTO, tight=True), width=450),
            actions=[ft.TextButton("Close", on_click=lambda e: setattr(dlg, 'open', False) or page.update())]
        )
        open_dialog_safe(page, dlg)

    # --- HOURS DETAILS DIALOG ---
    def open_hours_detail_dialog(e, w_id, w_name, start_date, end_date):
        c = db.conn.cursor()
        c.execute("SELECT date, shift, SUM(hours) FROM overtime_history WHERE worker_id=? AND date BETWEEN ? AND ? AND hours > 0 GROUP BY date, shift ORDER BY date", (w_id, start_date, end_date))
        rows = c.fetchall()
        
        list_items = [
            ft.Container(
                content=ft.Row([
                    ft.Text("Date", width=100, weight="bold", size=12, color=COLOR_TEXT_SUB),
                    ft.Text("Shift", width=100, weight="bold", size=12, color=COLOR_TEXT_SUB),
                    ft.Text("Hours", weight="bold", size=12, color=COLOR_TEXT_SUB, text_align=ft.TextAlign.RIGHT, expand=True)
                ]),
                padding=ft.Padding.only(bottom=10, left=10, right=10),
                border=ft.border.only(bottom=ft.border.BorderSide(2, COLOR_BORDER))
            )
        ]
        
        total_hrs = 0
        for r in rows:
            date_str = r[0]
            shift_val = r[1] if r[1] else "Morning"
            hrs = float(r[2])
            total_hrs += hrs
            
            list_items.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(date_str, width=100, size=13, weight="w600", color=COLOR_TEXT_MAIN),
                        ft.Text(shift_val, width=100, size=13, color=COLOR_TEXT_SUB),
                        ft.Text(f"{hrs:g} h", weight="bold", color=COLOR_PRIMARY, size=13, text_align=ft.TextAlign.RIGHT, expand=True)
                    ]),
                    padding=10, border=ft.border.only(bottom=ft.border.BorderSide(1, COLOR_BORDER))
                )
            )
            
        if len(list_items) == 1:
            list_items.append(ft.Container(content=ft.Text("No overtime hours found.", italic=True, color="grey"), padding=10))
        else:
            list_items.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text("Total Hours", weight="bold", size=14), 
                        ft.Text(f"{total_hrs:g} h", weight="bold", color=COLOR_PRIMARY, size=14)
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
                    padding=10, bgcolor="#F9FAFB"
                )
            )
            
        dlg = ft.AlertDialog(
            title=ft.Text(f"Overtime Hours: {w_name}", weight="bold", size=16),
            content=ft.Container(content=ft.Column(list_items, scroll=ft.ScrollMode.AUTO, tight=True), width=400),
            actions=[ft.TextButton("Close", on_click=lambda e: setattr(dlg, 'open', False) or page.update())]
        )
        open_dialog_safe(page, dlg)

    # --- PAY OVERTIME DIALOG ---
    def open_pay_ot_dialog(e, worker_id, w_name, total_unpaid, start_sql, end_sql):
        pay_amount_input = ft.TextField(
            label="Amount to Pay (PKR)", 
            value=str(int(total_unpaid)), 
            border_color="green", 
            border_radius=8, 
            autofocus=True
        )
        
        try:
            pay_amount_input.selection = ft.TextSelection(0, len(str(int(total_unpaid))))
        except AttributeError:
            pass
        
        def process_payment(e=None):
            try:
                actual_paid = float(pay_amount_input.value)
                
                c = db.conn.cursor()
                
                # Insert a single negative Unpaid record (Payment) to deduct from unpaid balance on the viewed date
                c.execute("INSERT INTO overtime_history (worker_id, date, amount, hours, status, shift) VALUES (?, ?, ?, 0, 'Unpaid', 'Payment')", (worker_id, end_sql, -actual_paid))
                
                # Insert a single positive Paid record to increase the paid balance on the viewed date
                c.execute("INSERT INTO overtime_history (worker_id, date, amount, hours, status, shift) VALUES (?, ?, ?, 0, 'Paid', 'Payment')", (worker_id, end_sql, actual_paid))
                
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
                    ft.Text("Payments are recorded as deductions from the unpaid balance.", color="grey", size=12),
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
        
        c.execute("SELECT worker_id, SUM(amount), SUM(hours) FROM overtime_history WHERE date BETWEEN ? AND ? AND (status='Unpaid' OR status IS NULL) GROUP BY worker_id", (start_sql, end_sql))
        unpaid_data = {row[0]: (row[1] or 0.0, row[2] or 0.0) for row in c.fetchall()}
        
        c.execute("SELECT worker_id, SUM(amount), SUM(hours) FROM overtime_history WHERE date BETWEEN ? AND ? AND status='Paid' GROUP BY worker_id", (start_sql, end_sql))
        paid_data = {row[0]: (row[1] or 0.0, row[2] or 0.0) for row in c.fetchall()}
        
        c.execute("SELECT worker_id, shift FROM overtime_history WHERE date BETWEEN ? AND ? AND hours > 0", (start_sql, end_sql))
        shift_data = {}
        for row in c.fetchall():
            wid = row[0]
            shift = row[1] if row[1] else "Morning"
            if wid not in shift_data:
                shift_data[wid] = set()
            if shift != "--":
                shift_data[wid].add(shift)
        
        for w in workers:
            w_id = w[0]
            w_name = w[1]
            w_type = w[6]
            w_custom_id = w[8]
            display_id = f"W-{w_custom_id}" if w_type == "Weekly" else f"M-{w_custom_id}"
            
            matches_search = True
            if query and query not in w_name.lower() and query not in display_id.lower():
                matches_search = False
            
            unpaid_amt, unpaid_hrs = unpaid_data.get(w_id, (0.0, 0.0))
            paid_amt, paid_hrs = paid_data.get(w_id, (0.0, 0.0))
            total_hrs = unpaid_hrs + paid_hrs
            
            # Identify if worker has any records in this period to keep the list clean
            is_participating = (unpaid_amt != 0 or paid_amt != 0 or total_hrs > 0)
            
            if matches_search:
                if is_participating:
                    total_unpaid_period += unpaid_amt
                    total_paid_period += paid_amt
                    participating_count += 1
            
            if not matches_search:
                continue
                
            # Filter out workers who have no overtime in this period
            if not is_participating:
                continue
                
            if filter_state["mode"] == "Unpaid" and unpaid_amt == 0:
                continue
            if filter_state["mode"] == "Paid" and paid_amt == 0:
                continue

            worker_shifts = shift_data.get(w_id, set())
            if "Morning" in worker_shifts and "Evening" in worker_shifts:
                shift_val = "Morning + Evening"
            elif "Morning" in worker_shifts:
                shift_val = "Morning"
            elif "Evening" in worker_shifts:
                shift_val = "Evening"
            else:
                shift_val = "--"

            unpaid_ui = ft.Text(f"{int(unpaid_amt):,} PKR", weight="bold", color="#F59E0B" if unpaid_amt > 0 else "grey", size=14)
            paid_ui = ft.Text(f"{int(paid_amt):,} PKR", weight="bold", color="#10B981" if paid_amt > 0 else "grey", size=14)
            shift_ui = ft.Text(shift_val, width=120, color=COLOR_TEXT_SUB, size=13)
            
            hrs_container = ft.Container(
                content=ft.Text(f"{total_hrs:g} h", weight="bold", color=COLOR_PRIMARY, size=13),
                ink=True,
                on_click=lambda e, wid=w_id, wn=w_name: open_hours_detail_dialog(e, wid, wn, start_sql, end_sql),
                tooltip="Click to view dates and shifts",
                width=60,
                padding=ft.Padding.symmetric(horizontal=4, vertical=4),
                border_radius=4,
            )
            
            add_btn = ft.ElevatedButton(
                "Add OT", 
                icon=ft.Icons.ADD, 
                bgcolor="#0284C7", 
                color="white", 
                height=35, 
                style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=10, vertical=0)),
                on_click=lambda e, wid=w_id, wn=w_name: open_add_ot_dialog(e, prefill_worker_id=wid, prefill_worker_name=wn)
            )
            
            pay_btn = ft.ElevatedButton(
                "Pay OT", 
                icon=ft.Icons.PAYMENTS, 
                bgcolor="#10B981" if unpaid_amt > 0 else "#E5E7EB", 
                color="white" if unpaid_amt > 0 else "grey", 
                height=35, 
                disabled=(unpaid_amt <= 0), 
                style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=10, vertical=0)),
                on_click=lambda e, wid=w_id, wn=w_name, unp=unpaid_amt: open_pay_ot_dialog(e, wid, wn, unp, start_sql, end_sql)
            )

            action_row = ft.Row([add_btn, pay_btn], spacing=5, alignment=ft.MainAxisAlignment.END, width=210)

            unpaid_container = ft.Container(
                content=unpaid_ui, width=90, ink=True, on_click=lambda e, wid=w_id, wn=w_name: open_unpaid_ot_dialog(e, wid, wn, start_sql, end_sql), tooltip="View Unpaid Details"
            )
            
            paid_container = ft.Container(
                content=paid_ui, width=90, ink=True, on_click=lambda e, wid=w_id, wn=w_name: open_paid_ot_dialog(e, wid, wn, start_sql, end_sql) if paid_amt > 0 else None, tooltip="View Paid Details" if paid_amt > 0 else None
            )

            def make_hover(idx):
                def hover(e):
                    e.control.bgcolor = "#F1F5F9" if e.data == "true" else ("white" if idx % 2 == 0 else "#FAFAFA")
                    e.control.update() 
                return hover

            new_list_controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(display_id, width=50, weight="w600", color=COLOR_TEXT_MAIN, size=13),
                        ft.Text(w_name, expand=True, weight="bold", color=COLOR_TEXT_MAIN, size=15),
                        ft.Text(w_type, width=60, color=COLOR_TEXT_SUB, size=13),
                        shift_ui,
                        hrs_container,
                        unpaid_container,
                        paid_container,
                        action_row
                    ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=ft.Padding.symmetric(vertical=8, horizontal=15), 
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
        
        final_ui_controls = []
        final_ui_controls.append(
            ft.Container(
                content=ft.Row([
                    ft.Text("ID", width=50, weight="bold", color=COLOR_TEXT_SUB, size=13),
                    ft.Text("Name", expand=True, weight="bold", color=COLOR_TEXT_SUB, size=13),
                    ft.Text("Type", width=60, weight="bold", color=COLOR_TEXT_SUB, size=13),
                    ft.Text("Shift", width=120, weight="bold", color=COLOR_TEXT_SUB, size=13),
                    ft.Text("Hours", width=60, weight="bold", color=COLOR_PRIMARY, size=13),
                    ft.Text("Unpaid OT", width=90, weight="bold", color="#F59E0B", size=13),
                    ft.Text("Paid OT", width=90, weight="bold", color="#10B981", size=13),
                    ft.Text("Action", width=210, weight="bold", color=COLOR_TEXT_SUB, size=13, text_align=ft.TextAlign.CENTER),
                ]),
                bgcolor=COLOR_BG_LIGHT, padding=ft.Padding.symmetric(vertical=10, horizontal=15), border=ft.border.only(bottom=ft.border.BorderSide(2, COLOR_BORDER))
            )
        )
        
        if len(new_list_controls) == 0:
            final_ui_controls.append(
                ft.Container(
                    content=ft.Text("No overtime recorded for this period. Use '+ Add Overtime' to begin.", color="grey", italic=True),
                    padding=30,
                    alignment=ft.Alignment(0, 0)
                )
            )
        else:
            final_ui_controls.extend(new_list_controls)
        
        ot_grid.controls = final_ui_controls
        
        try:
            stats_container.update()
            ot_grid.update()
        except:
            pass

        page.update()

    global_add_btn = ft.ElevatedButton(
        "Add Overtime", 
        icon=ft.Icons.ADD, 
        bgcolor=COLOR_PRIMARY, 
        color="white", 
        height=40,
        on_click=open_add_ot_dialog
    )

    top_row_1 = ft.Row([
        ft.Text("Overtime Management", size=22, weight="bold", color=COLOR_TEXT_MAIN),
        ft.Row([
            ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, on_click=lambda e: change_period(-1)),
            period_clickable,
            ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, on_click=lambda e: change_period(1)),
        ], alignment=ft.MainAxisAlignment.CENTER),
        ft.Row([
            search_input, 
            global_add_btn,
            ft.FilledButton("Today", icon=ft.Icons.TODAY, on_click=reset_to_today, bgcolor="#111827")
        ], spacing=10)
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

    top_row_2 = ft.Row([
        rate_input
    ], alignment=ft.MainAxisAlignment.START)

    main_view = ft.Container(
        content=ft.Column([
            top_row_1,
            top_row_2,
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