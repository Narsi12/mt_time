"""
static variables 
"""
home_page_file = "form.html"
detail_page_file = "filled.html"
error_page_file = "error.html"
individual_detail_file = "individual_detail.html"
date_format = "%d-%m-%Y"
mt = "MOURITECH"
holidays = ("07_Client Holiday", "04_MouriTech Holiday", "03_Personal Time Off")
read_schedule_file_columns = [
    "Emp. Id",
    "Project",
    "From Date",
    "To Date",
    "Billing Status",
    "Client",
    "Practice Area",
    "Effort(%)",
    "Type of Billing",
]
read_schedule_file_projects = ["Emp. Id", "Project", "Client", "Billing Status"]
mt_name_whitespace = "MOURI TECH  -Project"
mt_name = "MOURI TECH -Project"
partial_result_columns = ["Employee Number", "validation"]
partial_result_merge_columns = [
    "Filled Project",
    "Employee Number",
    "Employee Name",
    "Department",
    "Date",
    "Project Code",
    "Task",
    "Total Hours",
    "Filled Billing Type",
    "Reporting To",
    "Status",
    "Project Manager",
    "Client data",
    "validation",
    "Client Name",
    "Assigned Projects",
    "Digital Lead",
    "Comments"
]
dg_leads = [800356, 800416, 800686, 800732, 800762, 800930, 801130, 804094, 800625]
read_dt_file_compare_left = ["Employee Number", "Billing Type", "Project Name", "Task"]
read_dt_file_compare_right = ["Emp. Id", "Billing Status", "Project"]
projects_link_logs_columns = ["Emp. Id", "Project", "From Date", "To Date"]
mt_projects = {
    "Maternity",
    "MT_Bench",
    mt_name_whitespace,
    mt_name,
    "Client Selection",
    "MT_Freshers",
    "MT_Value Addition Group",
    "PIP",
}
customer_billing_tasks = ("01_Customer Billing", "09_Shadow Billing")
partial_result_merge_rename = {
    "0_y": "Assigned Projects",
    "Project Name": "Filled Project",
    "Billing Type": "Filled Billing Type",
    "valid_exclude_mt": "validation",
}
customer_non_billing_tasks = (
    "02_Customer Non Billable",
    "06_Learning",
    "10_Shadow Non Billable",
    "08_Admin/Meeting",
    "04_MouriTech Holiday",
    "12_Internal POC",
    "03_Personal Time Off",
    "07_Client Holiday",
    "13_Internal Product"
)
limited_read_schedule_file_rename = {"Effort(%)": "Effort %"}
