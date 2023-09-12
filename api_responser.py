import pandas as pd

def home_page(df):
    
    splited_data = df[['Employee Number', 'Employee Name', 'validation', 'Digital Lead', 'Reporting To', 'Project Manager']]
    splited_data['projects'] = df['Assigned Projects'].str.get(0)
    splited_data['clients'] = df['Assigned Projects'].str.get(1)
    
    splited_data['clients'] = splited_data['clients'].astype(str)
    splited_data['projects'] = splited_data['projects'].astype(str)
    grouped = splited_data.groupby(['Employee Number', 'Employee Name', 'validation', 'projects', 'clients']).agg({
    'Digital Lead': lambda x: list(set(x)),
    'Reporting To': lambda x: list(set(x)),
    'Project Manager': lambda x: list(set(x))
    }).reset_index()

    df_dict = grouped.to_dict(orient='records')
    
    return df_dict

def create_nested_dict(group):
    emp_data = group[['Employee Number', 'Employee Name']].iloc[0]
    emp_data['Department'] = list(set(group['Department']))
    emp_data['Project Manager'] =  list(set(group['Project Manager']))
    emp_data['Reporting To'] =  list(set(group['Reporting To']))
    
    # client_data = group['Client data'].iloc[0]
    client_data = group['Client data'].iloc[0]
    # print(client_data['Client data'])
    # Extract column names and data rows from the client_data dictionary
    columns = client_data["columns"]
    data_rows = client_data["data"]
    # Create a list of dictionaries by zipping column names and data rows
    client_data_list = [dict(zip(columns, row)) for row in data_rows]
    # time_sheets = group[['Date', 'Filled Project', 'Task', 'Client Name', 'Filled Billing Type', 'Total Hours', 'Status']].to_dict(orient='records')
    time_sheets = {
        'columns': ['Date', 'Filled Project', 'Task', 'Client Name', 'Filled Billing Type', 'Total Hours', 'Status'],
        'data': group[['Date', 'Filled Project', 'Task', 'Client Name', 'Filled Billing Type', 'Total Hours', 'Status']].values.tolist()
    }
    emp_dict = {
        'emp_data': emp_data.to_dict(),
        'Client data': client_data_list,
        'time_sheets': time_sheets
    }

    return emp_dict

def employee_detail(df):
       
    grouped_data = df.groupby('Employee Number').apply(create_nested_dict).to_dict()

    return grouped_data