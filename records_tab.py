import flet as ft
from datetime import datetime, timedelta

def get_records_view(page: ft.Page, db, state, show_snack, open_dialog_safe, reload_weekly_cb, reload_monthly_cb):
    COLOR_WHITE = "#ffffff"
    COLOR_GREY_300 = "#e0e0e0"
    COLOR_TEXT_MAIN = "#111827"
    COLOR_TEXT_SUB = "#4B5563"
    COLOR_BORDER = "#E5E7EB"
    COLOR_BG_LIGHT = "#F3F4F6"
    COLOR_PRIMARY = "#2D5B7A"

    records_list = ft.ListView(spacing=0, expand=True)
    records_label = ft.Text("", size=16, weight="bold")
    stats_container = ft.Container()

    # --- FILTER STATE INITIALIZATION ---
    if "rec_view_mode" not in state:
        state["rec_view_mode"] = "Month"
        state["rec_view_date"] = datetime.now()
        state["rec_start"] = datetime.now() - timedelta(days=7)
        state["rec_end"] = datetime.now()

    spec_in = ft.TextField(read_only=True, width=150, height=40, content_padding=10, text_align=ft.TextAlign.CENTER)
    start_in = ft.TextField(read_only=True, width=130, height=40, content_padding=10, text_align=ft.TextAlign.CENTER)
    end_in = ft.TextField(read_only=True, width=130, height=40, content_padding=10, text_align=ft.TextAlign.CENTER)

    safe_first = datetime(2000, 1, 1)
    safe_last = datetime(2035, 12, 31)

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
            
        current_mode = [state["rec_view_mode"]]
        chips_row = ft.Row(alignment=ft.MainAxisAlignment.CENTER, spacing=10)
        dynamic_content = ft.Container()

        months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        month_dd = ft.Dropdown(options=[ft.dropdown.Option(m) for m in months], value=state["rec_view_date"].strftime("%B"), width=145, border_radius=8)
        year_dd = ft.Dropdown(options=[ft.dropdown.Option(str(y)) for y in range(2020, 2035)], value=state["rec_view_date"].strftime("%Y"), width=145, border_radius=8)
        month_row = ft.Row([month_dd, year_dd], alignment=ft.MainAxisAlignment.CENTER)

        spec_in.value = state["rec_view_date"].strftime("%Y-%m-%d")
        
        def open_dp_spec_dialog(e):
            dp_spec.value = datetime.strptime(spec_in.value, "%Y-%m-%d")
            dp_spec.open = True
            page.update()
            
        spec_row = ft.Row([
            spec_in, 
            ft.IconButton(ft.Icons.CALENDAR_MONTH, icon_color=COLOR_PRIMARY, on_click=open_dp_spec_dialog)
        ], alignment=ft.MainAxisAlignment.CENTER)

        start_in.value = state["rec_start"].strftime("%Y-%m-%d")
        end_in.value = state["rec_end"].strftime("%Y-%m-%d")
        
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
            for m in ["Month", "Specific Date", "Date Range"]:
                is_active = (current_mode[0] == m)
                chip = ft.Container(
                    content=ft.Text(m, color="white" if is_active else COLOR_TEXT_SUB, weight="bold", size=12),
                    bgcolor=COLOR_PRIMARY if is_active else COLOR_BG_LIGHT,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8), border_radius=8, ink=True,
                    on_click=lambda e, selected=m: set_mode(selected)
                )
                chips_row.controls.append(chip)
            
            month_row.visible = (current_mode[0] == "Month")
            spec_row.visible = (current_mode[0] == "Specific Date")
            range_row.visible = (current_mode[0] == "Date Range")
            dynamic_content.content = ft.Column([month_row, spec_row, range_row], tight=True, alignment=ft.MainAxisAlignment.CENTER)

        def set_mode(new_mode):
            current_mode[0] = new_mode
            update_dialog_ui()
            page.update()

        update_dialog_ui()

        def apply_filter(e):
            state["rec_view_mode"] = current_mode[0]
            if current_mode[0] == "Month": 
                state["rec_view_date"] = datetime(int(year_dd.value), months.index(month_dd.value) + 1, 1)
            elif current_mode[0] == "Specific Date": 
                state["rec_view_date"] = datetime.strptime(spec_in.value, "%Y-%m-%d")
            else: 
                state["rec_start"] = datetime.strptime(start_in.value, "%Y-%m-%d")
                state["rec_end"] = datetime.strptime(end_in.value, "%Y-%m-%d")
                
            filter_dialog.open = False
            page.update()
            page.run_thread(load_records_ui)

        filter_dialog = ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.FILTER_ALT, color=COLOR_PRIMARY), ft.Text("Filter Records", weight="bold", size=18)]),
            content=ft.Container(content=ft.Column([chips_row, ft.Divider(height=10, color="transparent"), dynamic_content], tight=True), width=350, padding=10),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(filter_dialog, 'open', False) or page.update()), 
                ft.ElevatedButton("Apply Filter", bgcolor=COLOR_PRIMARY, color="white", on_click=apply_filter)
            ], shape=ft.RoundedRectangleBorder(radius=12)
        )
        page.overlay.append(filter_dialog)
        filter_dialog.open = True
        page.update()

    month_clickable = ft.Container(
        content=records_label, on_click=open_filter_dialog, ink=True, padding=ft.padding.symmetric(horizontal=10, vertical=5), border_radius=5, tooltip="Click to Change View Filter"
    )

    def with_opacity(opacity, hex_color):
        alpha = hex(int(opacity * 255))[2:].zfill(2).upper()
        base_color = hex_color.lstrip('#')
        if len(base_color) == 8: 
            base_color = base_color[2:]
        return f"#{alpha}{base_color}"

    current_filter = ["All"]
    filter_type_row = ft.Row(spacing=8)

    def set_filter(label): 
        current_filter[0] = label
        render_filters()
        page.run_thread(load_records_ui)

    def render_filters():
        filter_type_row.controls.clear()
        for label in ["All", "Weekly", "Monthly"]:
            is_active = current_filter[0] == label
            chip = ft.Container(
                content=ft.Text(label, weight="bold", size=12, color=COLOR_WHITE if is_active else COLOR_TEXT_SUB), 
                bgcolor=COLOR_PRIMARY if is_active else COLOR_BG_LIGHT, 
                padding=ft.padding.symmetric(horizontal=16, vertical=8), border_radius=20, border=ft.border.all(1, COLOR_PRIMARY if is_active else COLOR_BORDER), ink=True, 
                on_click=lambda e, l=label: set_filter(l)
            )
            filter_type_row.controls.append(chip)
        try: page.update()
        except: pass

    render_filters()
    
    search_input = ft.TextField(
        label="Search records by name...", width=250, border_radius=8, content_padding=12, border_color="#D1D5DB", bgcolor="#F9FAFB", 
        height=40, prefix_icon=ft.Icons.SEARCH, on_change=lambda e: page.run_thread(load_records_ui)
    )

    def change_period(direction=0):
        mode = state["rec_view_mode"]
        if mode == "Month":
            curr = state["rec_view_date"]
            new_m = curr.month + direction
            y_adj = 0
            if new_m > 12: 
                new_m = 1
                y_adj = 1
            elif new_m < 1: 
                new_m = 12
                y_adj = -1
            state["rec_view_date"] = curr.replace(month=new_m, year=curr.year + y_adj)
        elif mode == "Specific Date": 
            state["rec_view_date"] += timedelta(days=direction)
        else:
            delta = (state["rec_end"] - state["rec_start"]).days + 1
            state["rec_start"] += timedelta(days=direction * delta)
            state["rec_end"] += timedelta(days=direction * delta)
        page.run_thread(load_records_ui)

    def reset_to_today(e):
        state["rec_view_mode"] = "Specific Date"
        state["rec_view_date"] = datetime.now()
        page.run_thread(load_records_ui)

    def create_stat_card(title, value, icon, icon_color):
        return ft.Container(
            content=ft.Row([
                ft.Container(content=ft.Icon(icon, size=24, color=icon_color), bgcolor=with_opacity(0.15, icon_color), padding=10, border_radius=50), 
                ft.Column([ft.Text(title, size=12, color="grey700", weight="w600"), ft.Text(str(value), size=18, weight="bold", color=COLOR_TEXT_MAIN)], spacing=0)
            ]), expand=True, bgcolor="white", padding=15, border_radius=8, border=ft.border.all(1, COLOR_BORDER), shadow=ft.BoxShadow(spread_radius=1, blur_radius=2, color="#0A000000", offset=ft.Offset(0, 1))
        )

    def show_detail_dialog(e, record):
        r_id, start, end, name, r_type, total, saved = record
        
        # Independent Cursor Call inside Dialog to avoid conflicts
        c = db.conn.cursor()
        c.execute("SELECT id FROM workers WHERE name=?", (name,))
        res = c.fetchone()
        wid = res[0] if res else None
        
        if not wid: 
            show_snack(page, "Worker data not found.", "red"); return

        c.execute("SELECT date, amount_earned, status FROM attendance WHERE worker_id=? AND date BETWEEN ? AND ? ORDER BY date", (wid, start, end))
        att_data = c.fetchall()
        
        c.execute("SELECT date, amount, reason FROM advances WHERE worker_id=? AND date BETWEEN ? AND ? ORDER BY date", (wid, start, end))
        adv_data = c.fetchall()

        att_lookup = {row[0]: (row[1], row[2]) for row in att_data}
        att_status_map = {row[0]: row[2] for row in att_data}

        att_rows = []
        total_earned = 0
        s_date = datetime.strptime(start, "%Y-%m-%d")
        e_date = datetime.strptime(end, "%Y-%m-%d")
        curr_date = s_date
        
        while curr_date <= e_date:
            d_str = curr_date.strftime("%Y-%m-%d")
            if d_str in att_lookup:
                amt, st = att_lookup[d_str]
                status_color = "green" if st == "Present" else "red"
            else:
                amt = 0; st = "Not Marked"; status_color = "grey"
            total_earned += amt
            att_rows.append(ft.DataRow([ft.DataCell(ft.Text(d_str)), ft.DataCell(ft.Text(st, color=status_color)), ft.DataCell(ft.Text(str(int(amt))))]))
            curr_date += timedelta(days=1)

        att_table = ft.DataTable(columns=[ft.DataColumn(ft.Text("Date")), ft.DataColumn(ft.Text("Status")), ft.DataColumn(ft.Text("Earned"))], rows=att_rows, heading_row_height=40, border=ft.border.all(1, COLOR_BORDER))

        adv_rows = []
        for d, amt, rsn in adv_data:
            if att_status_map.get(d) == "Absent": 
                adv_rows.append(ft.DataRow([ft.DataCell(ft.Text(d)), ft.DataCell(ft.Text(f"{rsn} (Absent)", color="grey")), ft.DataCell(ft.Text(str(int(amt)), color="grey", style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH)))]))
            else: 
                adv_rows.append(ft.DataRow([ft.DataCell(ft.Text(d)), ft.DataCell(ft.Text(rsn)), ft.DataCell(ft.Text(str(int(amt))))]))

        adv_table = ft.DataTable(columns=[ft.DataColumn(ft.Text("Date")), ft.DataColumn(ft.Text("Reason")), ft.DataColumn(ft.Text("Amount"))], rows=adv_rows, heading_row_height=40, border=ft.border.all(1, COLOR_BORDER))

        summary_text = ft.Column([ft.Text(f"Total Earned: {int(total_earned)}", weight="bold"), ft.Text(f"Total Deductions (Advances/Absents): -{int(total_earned - total)}", color="red"), ft.Divider(), ft.Text(f"Net Paid: {int(total)} PKR", size=20, weight="bold", color="green")])
        dlg = ft.AlertDialog(title=ft.Text(f"Payment Record: {name} ({r_type})", weight="bold"), content=ft.Container(content=ft.Column([ft.Text("Attendance Breakdown", weight="bold"), ft.Container(content=ft.Column([att_table]), border_radius=5, padding=5), ft.Divider(), ft.Text("Advances Breakdown", weight="bold"), ft.Container(content=ft.Column([adv_table]), border_radius=5, padding=5), ft.Divider(), summary_text], scroll=ft.ScrollMode.AUTO), width=600, height=700), actions=[ft.TextButton("Close", on_click=lambda e: setattr(dlg, 'open', False) or page.update())])
        open_dialog_safe(page, dlg)

    def delete_record_bg(r_id):
        db.delete_record(r_id)
        load_records_ui()
        reload_weekly_cb()
        reload_monthly_cb()
        show_snack(page, "Record Deleted", "red")

    def load_records_ui(e=None):
        # UI BATCHING AND INDEPENDENT CURSOR
        new_list_controls = []
        mode = state["rec_view_mode"]
        search_query = search_input.value.lower() if search_input.value else ""
        
        c = db.conn.cursor()
        filter_str = ""
        
        if mode == "Month":
            filter_str = state["rec_view_date"].strftime("%Y-%m")
            records_label.value = state["rec_view_date"].strftime("%B %Y")
        elif mode == "Specific Date":
            filter_str = state["rec_view_date"].strftime("%Y-%m-%d")
            records_label.value = state["rec_view_date"].strftime("%d %b %Y")
        else:
            s_date = state["rec_start"]
            e_date = state["rec_end"]
            records_label.value = f"{s_date.strftime('%d %b %Y')} - {e_date.strftime('%d %b %Y')}"

        sql = "SELECT * FROM records WHERE date_saved LIKE ?"
        params = [f"{filter_str}%"]
        
        if current_filter[0] != "All":
            sql += " AND salary_type = ?"
            params.append(current_filter[0])
            
        sql += " ORDER BY id DESC"
        
        c.execute(sql, tuple(params))
        all_records = c.fetchall()
        
        # Apply python-level filter for Data Range mode
        if mode == "Date Range":
            records = [r for r in all_records if s_date <= datetime.strptime(r[6], "%Y-%m-%d") <= e_date]
        else:
            records = all_records

        filtered_records = []
        total_payouts = 0
        for r in records:
            if search_query and search_query not in r[3].lower(): 
                continue
            filtered_records.append(r)
            total_payouts += r[5]

        stats_container.content = ft.Row([
            create_stat_card("Total Records", len(filtered_records), ft.Icons.RECEIPT_LONG, "#3B82F6"), 
            create_stat_card("Total Payouts", f"{int(total_payouts):,} PKR", ft.Icons.ACCOUNT_BALANCE_WALLET, "#10B981")
        ], spacing=15)

        new_list_controls.append(
            ft.Container(
                content=ft.Row([
                    ft.Text("Date Saved", width=120, weight="bold", color=COLOR_TEXT_SUB, size=13), 
                    ft.Text("Name", width=180, weight="bold", color=COLOR_TEXT_SUB, size=13), 
                    ft.Text("Type", width=100, weight="bold", color=COLOR_TEXT_SUB, size=13), 
                    ft.Text("Period", expand=True, weight="bold", color=COLOR_TEXT_SUB, size=13), 
                    ft.Text("Total Paid", width=150, weight="bold", color=COLOR_TEXT_SUB, size=13), 
                    ft.Text("Action", width=100, weight="bold", color=COLOR_TEXT_SUB, size=13, text_align=ft.TextAlign.CENTER)
                ]), 
                bgcolor=COLOR_BG_LIGHT, padding=ft.padding.symmetric(vertical=10, horizontal=15), border=ft.border.only(bottom=ft.border.BorderSide(2, COLOR_BORDER))
            )
        )
        
        # ISOLATED HOVER
        def make_hover(idx):
            def hover(ev):
                ev.control.bgcolor = "#F1F5F9" if ev.data == "true" else ("white" if idx % 2 == 0 else "#FAFAFA")
                ev.control.update() 
            return hover

        if not filtered_records: 
            new_list_controls.append(ft.Container(content=ft.Text("No records found.", italic=True, color="grey"), padding=20))
        else:
            for index, r in enumerate(filtered_records):
                type_color = "#10B981" if r[4].lower() == "monthly" else "#F59E0B"
                type_bg = "#D1FAE5" if r[4].lower() == "monthly" else "#FEF3C7"
                type_container = ft.Container(content=ft.Text(r[4].upper(), size=10, weight="bold", color=type_color), bgcolor=type_bg, padding=ft.padding.symmetric(horizontal=8, vertical=4), border_radius=4)

                new_list_controls.append(
                    ft.Container(
                        content=ft.Row([
                            ft.Text(r[6], width=120, color=COLOR_TEXT_MAIN, size=13), 
                            ft.Text(r[3], width=180, weight="bold", color=COLOR_TEXT_MAIN, size=15), 
                            ft.Container(content=type_container, width=100), 
                            ft.Text(f"{r[1]} to {r[2]}", expand=True, size=13, color=COLOR_TEXT_SUB), 
                            ft.Text(f"{int(r[5]):,} PKR", width=150, weight="bold", color="#10B981", size=14), 
                            ft.Row([
                                ft.IconButton(icon=ft.Icons.VISIBILITY, icon_color="#3B82F6", on_click=lambda e, rec=r: show_detail_dialog(e, rec), tooltip="View Details", icon_size=18, width=32, height=32), 
                                ft.IconButton(icon=ft.Icons.DELETE, icon_color="#EF4444", on_click=lambda e, rid=r[0]: page.run_thread(delete_record_bg, rid), tooltip="Delete", icon_size=18, width=32, height=32)
                            ], width=100, spacing=0, alignment=ft.MainAxisAlignment.CENTER)
                        ], vertical_alignment=ft.CrossAxisAlignment.CENTER), 
                        padding=ft.padding.symmetric(vertical=8, horizontal=15), bgcolor="white" if index % 2 == 0 else "#FAFAFA", border=ft.border.only(bottom=ft.border.BorderSide(1, COLOR_BORDER)), 
                        on_hover=make_hover(index)
                    )
                )
                
        # PUSH ALL UPDATES TO SCREEN AT ONCE
        records_list.controls = new_list_controls
        try: 
            stats_container.update()
            records_list.update()
        except: pass
        page.update()

    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Text("Payment Records", size=22, weight="bold", color=COLOR_TEXT_MAIN), 
                ft.Row([
                    ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: change_period(-1)), 
                    month_clickable, 
                    ft.IconButton(icon=ft.Icons.ARROW_FORWARD, on_click=lambda e: change_period(1)),
                    ft.TextButton("Today", icon=ft.Icons.TODAY, on_click=reset_to_today, style=ft.ButtonStyle(color=COLOR_PRIMARY))
                ], alignment=ft.MainAxisAlignment.CENTER), 
                ft.Row([filter_type_row, search_input], spacing=15, vertical_alignment=ft.CrossAxisAlignment.CENTER)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), 
            ft.Divider(height=5, color="transparent"), 
            stats_container, ft.Divider(height=5, color="transparent"), 
            ft.Container(content=records_list, expand=True, bgcolor="white", border_radius=8, border=ft.border.all(1, COLOR_BORDER), shadow=ft.BoxShadow(spread_radius=1, blur_radius=2, color="#0D000000", offset=ft.Offset(0, 1)), clip_behavior=ft.ClipBehavior.HARD_EDGE)
        ], expand=True), visible=False
    ), load_records_ui