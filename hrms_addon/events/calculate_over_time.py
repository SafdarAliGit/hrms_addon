from datetime import datetime, date

today = date.today()
import frappe
from hrms_addon.util.get_doctype_by_field import get_doctype_by_field


def submit(self, method=None):
    if self.in_time and self.out_time:
        employee = frappe.get_doc("Employee", self.employee)

        if not employee.default_shift:
            frappe.throw("Shift Type Not Found in Employee Checkin")

        default_shift_type = frappe.get_doc("Shift Type", employee.default_shift)

        last_out_datetime = datetime.combine(today, self.out_time.time())
        shift_start_datetime = datetime.combine(today, (datetime.min + default_shift_type.start_time).time())
        shift_end_datetime = datetime.combine(today, (datetime.min + default_shift_type.end_time).time())

        if self.in_time < shift_start_datetime:
            entry_datetime = shift_start_datetime

        over_time = (last_out_datetime - shift_end_datetime).total_seconds() / 3600

        if (over_time > 0.5 and employee.department == "Production"):
            # Create Daily Over Time
            timesheet_doc = frappe.new_doc("Timesheet")
            timesheet_doc.employee = self.employee
            timesheet_doc.custom_attendance = self.name
            timesheet_detail = timesheet_doc.append("time_logs", {})
            timesheet_detail.activity_type = "Execution"
            timesheet_detail.from_time = shift_end_datetime
            timesheet_detail.to_time = last_out_datetime
            timesheet_detail.custom_checkin_time = entry_datetime
            timesheet_detail.custom_checkout_time = last_out_datetime
            timesheet_detail.hours = over_time
            timesheet_doc.save()

        frappe.db.set_value(self.doctype, self.name, {
            "custom_shift_start_time": entry_datetime,
            "custom_shift_end_time": shift_end_datetime,
            "custom_exit_time": last_out_datetime,
            "custom_over_time": over_time
        })
        frappe.db.commit()


def save(self, method=None):
    # Get the current year and month
    current_date = datetime.now()
    current_year = current_date.year
    current_month = current_date.month

    # Query to count late entries for the current month for the given employee
    count = frappe.db.count('Attendance', filters={
        'attendance_date': ['like', f'{current_year}-{current_month:02d}%'],  # Match year-month
        'employee': self.employee,
        'late_entry': 1  # Only count late entries
    })

    # Update the custom late entry count field
    if self.late_entry == 1:
        count +=1
        self.custom_late_entry_cout = count
    self.custom_late_entry_cout = count

    days_for_absent_mark = frappe.db.get_single_value("Attendance Settings", 'days_for_absent_mark')
    if count > 0 and count % days_for_absent_mark == 0:
        self.status = "Absent"

def cancel(self, method=None):
    ts = get_doctype_by_field('Timesheet', 'custom_attendance', self.name)
    if ts:
        ts.cancel()
        frappe.db.commit()
