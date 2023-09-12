import pandas as pd, json, datetime

try:
    from .config import *
except:
    from config import *


def extraction_pandas(schedule_file, dt_file):
    prjts_billing = []
    validate = {}
    track_valid_projects = {}
    # read schedule file
    read_schedule_file = pd.read_excel(schedule_file)
    read_schedule_file.fillna('', inplace=True)
    # read logs file
    read_dt_file = pd.read_excel(dt_file)
    read_dt_file.fillna('', inplace=True)
   
    grouped = read_dt_file[['Employee Number', 'Date']].groupby('Employee Number')
    
    sdt_date = read_dt_file['Date'].min()
    edt_date = read_dt_file['Date'].max()
    unsubmitted_employees = []
    for group_name, group_df in grouped:
        try:
            s_date = read_schedule_file[read_schedule_file["Emp. Id"]==group_name]["From Date"].min()

            e_date = read_schedule_file[read_schedule_file["Emp. Id"]==group_name]["To Date"].max()
            
            b_dates = pd.bdate_range(start=s_date if sdt_date < s_date else sdt_date, end=e_date if edt_date > e_date else edt_date)
            
            missing_dates = b_dates[~b_dates.isin(group_df['Date'])]
            if missing_dates.isnull().all() == False:
                unsubmitted_employees.append(group_name)
        except Exception as e:
            print(e, group_name)
        
    read_schedule_file.drop(
        read_schedule_file.index[(read_schedule_file["Emp. Id"].isin(dg_leads))],
        axis=0,
        inplace=True,
    )
    read_dt_file.drop(
        read_dt_file.index[(read_dt_file["Employee Number"].isin(dg_leads))],
        axis=0,
        inplace=True,
    )

    projects_link_logs = read_schedule_file[projects_link_logs_columns]
    projects_link_logs = projects_link_logs.groupby(["Emp. Id"]).apply(
        lambda x: x.to_dict(orient="records")
    )

    copy_mt_project_list = set(
        read_dt_file[read_dt_file["Client Name"] == mt]["Project Name"].to_list()
        + read_schedule_file[
            (read_schedule_file["Client"] == mt)
            | (read_schedule_file["Client"] == "Maternity")
            | (read_schedule_file["Client"] == "Client Selections")
            | (read_schedule_file["Client"] == "MT BENCH")
            | (read_schedule_file["Client"] == "PIP")
        ]["Project"].to_list()
    )

    client_projects_only = (
        set(
            read_schedule_file["Project"].to_list()
            + read_dt_file["Project Name"].to_list()
        )
        - copy_mt_project_list
    )

    internal_pocs_only = copy_mt_project_list - mt_projects

    # pulling required columns from schedule file
    limited_read_schedule_file = read_schedule_file[read_schedule_file_columns]
    limited_read_schedule_file = limited_read_schedule_file.rename(
        index=str,
        columns=limited_read_schedule_file_rename,
    )
    # pulling list of projects which were assign to employee
    limited_read_schedule_file_with_projects = read_schedule_file[
        read_schedule_file_projects
    ]

    # manipulate the employee client details json list for easy validation
    json_agg_data = (
        limited_read_schedule_file.groupby("Emp. Id")
        .apply(lambda x: x.to_dict(orient="records"))
        .to_frame()
    )

    def extra_data(x):
        # convert each employee projects , clients and billings as individual list
        project_list = x.Project.to_list()
        client_list = x.Client.to_list()
        billing_types = x["Billing Status"].to_list()
        return [project_list, client_list, dict(zip(project_list, billing_types))]

    # manipulate the employee clients, projects and billing types json list for ui easy styling purpose
    json_agg_data_with_projects = (
        limited_read_schedule_file_with_projects.groupby("Emp. Id")
        .apply(lambda x: extra_data(x))
        .to_frame()
    )

    # merge the client details to employee logs
    merge_records = pd.merge(
        read_dt_file,
        json_agg_data,
        right_on="Emp. Id",
        left_on="Employee Number",
        how="inner",
    )
    # merge the client details employee logs merged dataset to list of projects dataset
    merge_records_projects = pd.merge(
        merge_records,
        json_agg_data_with_projects,
        right_on="Emp. Id",
        left_on="Employee Number",
        how="inner",
    )

    def add_project_intime(x):
        projects_link = []
        for i in projects_link_logs[x["Employee Number"]]:
            if (x["Date"] >= i["From Date"]) & (x["Date"] <= i["To Date"]):
                projects_link.append(i["Project"])
        return projects_link if projects_link else ["OUT_OF_RANGE"]

    merge_records_projects["prjts"] = merge_records_projects.apply(
        lambda x: add_project_intime(x), axis=1
    )

    # validation start here
    for index, row in merge_records_projects.iterrows():

        out_of_range = []
        for rep, client in enumerate(row["0_x"], 1):

            # checking the employee log file records with employee assigned projects date range
            if (row["Date"] >= client["From Date"]) & (
                row["Date"] <= client["To Date"]
            ):
                # checking if project is in assigned projects list
                if (row["Project Name"] in row["prjts"]) and (
                    row["Project Name"] == client["Project"]
                ):
                    # checking if billing type is in assigned billing type
                    if row["Billing Type"] == client["Billing Status"] and (
                        (
                            (row["Task"] in customer_billing_tasks)
                            and (row["Billing Type"] == "Billable")
                        )
                        or (
                            (row["Task"] in customer_non_billing_tasks)
                            and (row["Billing Type"] == "Non Billable")
                        )
                    ):
                        if client["Type of Billing"] == "Shadow Billable":
                            if (
                                row["Task"] == "09_Shadow Billing"
                                and client["Billing Status"] == "Billable"
                            ):

                                if row["Employee Number"] in track_valid_projects:
                                    track_valid_projects[row["Employee Number"]].append(
                                        row["Project Name"]
                                    )
                                else:
                                    track_valid_projects[row["Employee Number"]] = [
                                        row["Project Name"]
                                    ]

                                # track the log record and break the loop
                                if row["Employee Number"] in validate:
                                    validate[row["Employee Number"]].append(True)
                                    break
                                else:
                                    validate[row["Employee Number"]] = [True]
                                    break
                            else:
                                out_of_range.append(False)

                        elif client["Type of Billing"] == "Shadow Non Billable":

                            if (
                                row["Task"] == "10_Shadow Non Billable"
                                and client["Billing Status"] == "Non Billable"
                            ):

                                if row["Employee Number"] in track_valid_projects:
                                    track_valid_projects[row["Employee Number"]].append(
                                        row["Project Name"]
                                    )
                                else:
                                    track_valid_projects[row["Employee Number"]] = [
                                        row["Project Name"]
                                    ]

                                # track the log record and break the loop
                                if row["Employee Number"] in validate:
                                    validate[row["Employee Number"]].append(True)
                                    break
                                else:
                                    validate[row["Employee Number"]] = [True]
                                    break
                            else:
                                out_of_range.append(False)
                        else:
                            if (
                                row["Task"] == customer_billing_tasks[0]
                                and client["Billing Status"] == "Billable" and row["Project Name"] not in mt_projects
                            ):
                                if row["Employee Number"] in track_valid_projects:
                                    track_valid_projects[row["Employee Number"]].append(
                                        row["Project Name"]
                                    )
                                else:
                                    track_valid_projects[row["Employee Number"]] = [
                                        row["Project Name"]
                                    ]
                                # track the log record and break the loop
                                if row["Employee Number"] in validate:
                                    validate[row["Employee Number"]].append(True)
                                    break
                                else:
                                    validate[row["Employee Number"]] = [True]
                                    break

                            elif (
                                row["Task"] == customer_non_billing_tasks[0]
                                and client["Billing Status"] == "Non Billable" and row["Project Name"] not in mt_projects
                            ):
                                if row["Employee Number"] in track_valid_projects:
                                    track_valid_projects[row["Employee Number"]].append(
                                        row["Project Name"]
                                    )
                                else:
                                    track_valid_projects[row["Employee Number"]] = [
                                        row["Project Name"]
                                    ]
                                # track the log record and break the loop
                                if row["Employee Number"] in validate:
                                    validate[row["Employee Number"]].append(True)
                                    break
                                else:
                                    validate[row["Employee Number"]] = [True]
                                    break

                            elif (
                                row["Project Name"] in mt_projects
                            ):
                            
                                if row["Employee Number"] in track_valid_projects:
                                    track_valid_projects[row["Employee Number"]].append(
                                        row["Project Name"]
                                    )
                                else:
                                    track_valid_projects[row["Employee Number"]] = [
                                        row["Project Name"]
                                    ]
                                # track the log record and break the loop
                                if row["Employee Number"] in validate:
                                    validate[row["Employee Number"]].append(True)
                                    break
                                else:
                                    validate[row["Employee Number"]] = [True]
                                    break
                            elif row["Task"] in holidays:

                                if row["Employee Number"] in track_valid_projects:
                                    track_valid_projects[row["Employee Number"]].append(
                                        "EMP_LEAVE"
                                    )
                                else:
                                    track_valid_projects[row["Employee Number"]] = ["EMP_LEAVE"]
                                if row["Employee Number"] in validate:
                                    validate[row["Employee Number"]].append(True)
                                    break
                                else:
                                    validate[row["Employee Number"]] = [True]
                                    break
                            else:
                                
                                out_of_range.append(False)
                            
                    elif row["Task"] in holidays:

                        # if billing type not satisfied, will check task is in under holiday or leave

                        if row["Employee Number"] in track_valid_projects:
                            track_valid_projects[row["Employee Number"]].append(
                                "EMP_LEAVE"
                            )
                        else:
                            track_valid_projects[row["Employee Number"]] = ["EMP_LEAVE"]
                        if row["Employee Number"] in validate:
                            validate[row["Employee Number"]].append(True)
                            break
                        else:
                            validate[row["Employee Number"]] = [True]
                            break
                    else:
                        out_of_range.append(False)

                elif (row["Project Name"] == mt_name_whitespace) or (
                    row["Project Name"] == mt_name
                ):
                    # checking if project is mouritech default project or not

                    if row["Employee Number"] in track_valid_projects:
                        track_valid_projects[row["Employee Number"]].append(
                            row["Project Name"]
                        )
                    else:
                        track_valid_projects[row["Employee Number"]] = [
                            row["Project Name"]
                        ]
                    if row["Employee Number"] in validate:
                        validate[row["Employee Number"]].append(True)
                        break
                    else:
                        validate[row["Employee Number"]] = [True]
                        break
                else:
                    # track the log record as non out of range record
                    out_of_range.append(False)

            elif (row["Project Name"] == mt_name_whitespace) or (
                row["Project Name"] == mt_name
            ):
                # checking if project is mouritech default project or not

                if row["Employee Number"] in track_valid_projects:
                    track_valid_projects[row["Employee Number"]].append("OUT_OF_RANGE")
                else:
                    track_valid_projects[row["Employee Number"]] = ["OUT_OF_RANGE"]
                if row["Employee Number"] in validate:
                    validate[row["Employee Number"]].append(True)
                    break
                else:
                    validate[row["Employee Number"]] = [True]
                    break

        else:

            # check record is in out of range of assigned dates
            if False in out_of_range:

                if row["Employee Number"] in validate:
                    validate[row["Employee Number"]].append(False)
                else:
                    validate[row["Employee Number"]] = [False]
            else:

                if row["Employee Number"] in track_valid_projects:
                    track_valid_projects[row["Employee Number"]].append("OUT_OF_RANGE")
                else:
                    track_valid_projects[row["Employee Number"]] = ["OUT_OF_RANGE"]
                if row["Employee Number"] in validate:
                    validate[row["Employee Number"]].append(True)
                else:
                    validate[row["Employee Number"]] = [True]

    validate_dict = {key: all(value) for key, value in validate.items()}

    # find out valid and invalid records
    partial_result = pd.DataFrame(validate_dict.items(), columns=partial_result_columns)
    # add valid and invalid status to result dataset
    partial_result_merge = pd.merge(merge_records_projects, partial_result, how="inner")

    valid_projects_df = pd.DataFrame(
        {key: set(value) for key, value in track_valid_projects.items()}.items(),
        columns=["Employee Number", "all_valid_projects"],
    )

    valid_projects_df_partial_result = pd.merge(
        partial_result_merge, valid_projects_df, how="left"
    )

    track_valid_projects_exclude_mt = {}
    valid_projects_df_partial_result_true = valid_projects_df_partial_result[
        valid_projects_df_partial_result["validation"] == True
    ]

    copy_mt_project_list_poc = []
    d = {}

    for index, x in valid_projects_df_partial_result_true.iterrows():

        if not x["Employee Number"] in d:
            d[x["Employee Number"]] = {}

        if set(x["0_y"][0]).issubset(copy_mt_project_list):

            if len(x["0_y"][0]) == 1:
                if x["prjts"][0] not in d[x["Employee Number"]]:
                    d[x["Employee Number"]][x["prjts"][0]] = []

                if x["0_y"][0][0] in mt_projects:

                    if x["Project Name"] in (mt_name_whitespace, mt_name):

                        if x["Employee Number"] in track_valid_projects_exclude_mt:
                            track_valid_projects_exclude_mt[
                                x["Employee Number"]
                            ].append(True)
                        else:
                            track_valid_projects_exclude_mt[x["Employee Number"]] = [
                                True
                            ]
                elif x["0_y"][0][0] == x["Project Name"]:

                    d[x["Employee Number"]][x["prjts"][0]].append(True)

                    if x["Employee Number"] in track_valid_projects_exclude_mt:
                        track_valid_projects_exclude_mt[x["Employee Number"]].append(
                            True
                        )
                    else:
                        track_valid_projects_exclude_mt[x["Employee Number"]] = [True]
                elif (
                    len(x["all_valid_projects"]) == 1
                    and list(x["all_valid_projects"])[0] == "EMP_LEAVE"
                ):
                    d[x["Employee Number"]][x["prjts"][0]].append("LEAVE")
                    if x["Employee Number"] in track_valid_projects_exclude_mt:
                        track_valid_projects_exclude_mt[x["Employee Number"]].append(
                            True
                        )

                    else:
                        track_valid_projects_exclude_mt[x["Employee Number"]] = [True]
                elif (
                    len(x["all_valid_projects"]) == 1
                    and list(x["all_valid_projects"])[0] == "OUT_OF_RANGE"
                ):
                    d[x["Employee Number"]][x["prjts"][0]].append("OUT_OF_RANGE")
                    if x["Employee Number"] in track_valid_projects_exclude_mt:
                        track_valid_projects_exclude_mt[x["Employee Number"]].append(
                            True
                        )
                    else:
                        track_valid_projects_exclude_mt[x["Employee Number"]] = [True]

                elif len(x["all_valid_projects"]) == 2:
                    if (
                        list(x["all_valid_projects"])[0] == "OUT_OF_RANGE"
                        and list(x["all_valid_projects"])[1] == "EMP_LEAVE"
                    ):
                        d[x["Employee Number"]][x["prjts"][0]].append("OUT_OF_RANGE")
                        d[x["Employee Number"]][x["prjts"][0]].append("LEAVE")
                        if x["Employee Number"] in track_valid_projects_exclude_mt:
                            track_valid_projects_exclude_mt[
                                x["Employee Number"]
                            ].append(True)
                        else:
                            track_valid_projects_exclude_mt[x["Employee Number"]] = [
                                True
                            ]
                    elif (
                        list(x["all_valid_projects"])[1] == "OUT_OF_RANGE"
                        and list(x["all_valid_projects"])[0] == "EMP_LEAVE"
                    ):

                        d[x["Employee Number"]][x["prjts"][0]].append("OUT_OF_RANGE")
                        d[x["Employee Number"]][x["prjts"][0]].append("LEAVE")
                        if x["Employee Number"] in track_valid_projects_exclude_mt:
                            track_valid_projects_exclude_mt[
                                x["Employee Number"]
                            ].append(True)
                        else:
                            track_valid_projects_exclude_mt[x["Employee Number"]] = [
                                True
                            ]
                    else:
                        if x["prjts"][0] not in mt_projects:
                            if x["Task"] in holidays:
                                for i in x["prjts"]:
                                    d[x["Employee Number"]][i].append("LEAVE")
                            else:
                                for i in x["prjts"]:
                                    d[x["Employee Number"]][i].append(False)

                else:
                    if x["prjts"][0] not in mt_projects:
                        if x["Task"] in holidays:
                            d[x["Employee Number"]][x["prjts"][0]].append("LEAVE")
                        else:
                            d[x["Employee Number"]][x["prjts"][0]].append(False)

            else:
                for i in x["prjts"]:
                    if i not in d[x["Employee Number"]]:
                        d[x["Employee Number"]][i] = []
                d[x["Employee Number"]][mt_name_whitespace] = []
                d[x["Employee Number"]][mt_name] = []
                if set(x["prjts"]).issubset(mt_projects):
                    if x["Project Name"] in (mt_name_whitespace, mt_name):

                        if x["Employee Number"] in track_valid_projects_exclude_mt:
                            track_valid_projects_exclude_mt[
                                x["Employee Number"]
                            ].append(True)
                        else:
                            track_valid_projects_exclude_mt[x["Employee Number"]] = [
                                True
                            ]
                else:
                    pocs = set(x["prjts"]) - mt_projects

                    if x["Project Name"] in pocs:
                        d[x["Employee Number"]][x["Project Name"]].append(True)
                        if x["Employee Number"] in track_valid_projects_exclude_mt:
                            track_valid_projects_exclude_mt[
                                x["Employee Number"]
                            ].append(True)
                        else:
                            track_valid_projects_exclude_mt[x["Employee Number"]] = [
                                True
                            ]
                    elif (
                        len(x["all_valid_projects"]) == 1
                        and list(x["all_valid_projects"])[0] == "EMP_LEAVE"
                    ):
                        for i in x["prjts"]:
                            if i not in d[x["Employee Number"]]:
                                d[x["Employee Number"]][i] = ["LEAVE"]
                            else:
                                d[x["Employee Number"]][i].append("LEAVE")
                        if x["Employee Number"] in track_valid_projects_exclude_mt:
                            track_valid_projects_exclude_mt[
                                x["Employee Number"]
                            ].append(True)

                        else:
                            track_valid_projects_exclude_mt[x["Employee Number"]] = [
                                True
                            ]
                    elif (
                        len(x["all_valid_projects"]) == 1
                        and list(x["all_valid_projects"])[0] == "OUT_OF_RANGE"
                    ):

                        if x["Employee Number"] in track_valid_projects_exclude_mt:
                            track_valid_projects_exclude_mt[
                                x["Employee Number"]
                            ].append(True)
                        else:
                            track_valid_projects_exclude_mt[x["Employee Number"]] = [
                                True
                            ]

                    elif len(x["all_valid_projects"]) == 2:
                        if (
                            list(x["all_valid_projects"])[0] == "OUT_OF_RANGE"
                            and list(x["all_valid_projects"])[1] == "EMP_LEAVE"
                        ):

                            for i in x["prjts"]:
                                if i not in d[x["Employee Number"]]:
                                    d[x["Employee Number"]][i] = ["LEAVE"]
                                else:
                                    d[x["Employee Number"]][i].append("LEAVE")
                            if x["Employee Number"] in track_valid_projects_exclude_mt:
                                track_valid_projects_exclude_mt[
                                    x["Employee Number"]
                                ].append(True)
                            else:
                                track_valid_projects_exclude_mt[
                                    x["Employee Number"]
                                ] = [True]
                        elif (
                            list(x["all_valid_projects"])[1] == "OUT_OF_RANGE"
                            and list(x["all_valid_projects"])[0] == "EMP_LEAVE"
                        ):

                            for i in x["prjts"]:
                                if i not in d[x["Employee Number"]]:
                                    d[x["Employee Number"]][i] = ["LEAVE"]
                                else:
                                    d[x["Employee Number"]][i].append("LEAVE")
                            if x["Employee Number"] in track_valid_projects_exclude_mt:
                                track_valid_projects_exclude_mt[
                                    x["Employee Number"]
                                ].append(True)
                            else:
                                track_valid_projects_exclude_mt[
                                    x["Employee Number"]
                                ] = [True]
                        else:
                            if x["Task"] in holidays:
                                for i in x["prjts"]:
                                    d[x["Employee Number"]][i].append("LEAVE")
                            else:
                                for i in x["prjts"]:
                                    d[x["Employee Number"]][i].append(False)

                    else:
                        if x["Task"] in holidays:
                            for i in x["prjts"]:
                                d[x["Employee Number"]][i].append("LEAVE")
                        else:
                            for i in x["prjts"]:
                                d[x["Employee Number"]][i].append(False)

        else:
            for i in x["prjts"]:
                if i not in d[x["Employee Number"]]:
                    d[x["Employee Number"]][i] = []
            d[x["Employee Number"]][mt_name_whitespace] = []
            d[x["Employee Number"]][mt_name] = []
            if x["Project Name"] in x["prjts"] and (
                x["Project Name"] not in copy_mt_project_list
            ):
                d[x["Employee Number"]][x["Project Name"]].append(True)
                if x["Employee Number"] in track_valid_projects_exclude_mt:
                    track_valid_projects_exclude_mt[x["Employee Number"]].append(True)
                else:
                    track_valid_projects_exclude_mt[x["Employee Number"]] = [True]

            elif set(x["prjts"]).issubset(mt_projects) and x["Project Name"] in (
                mt_name_whitespace,
                mt_name,
            ):

                if x["Employee Number"] in track_valid_projects_exclude_mt:
                    track_valid_projects_exclude_mt[x["Employee Number"]].append(True)

                else:
                    track_valid_projects_exclude_mt[x["Employee Number"]] = [True]

            elif set(x["prjts"]).issubset(copy_mt_project_list):

                if x["Project Name"] not in mt_projects:
                    d[x["Employee Number"]][x["Project Name"]].append(True)
                    if x["Employee Number"] in track_valid_projects_exclude_mt:
                        track_valid_projects_exclude_mt[x["Employee Number"]].append(
                            True
                        )

                    else:
                        track_valid_projects_exclude_mt[x["Employee Number"]] = [True]

            elif (
                len(x["all_valid_projects"]) == 1
                and list(x["all_valid_projects"])[0] == "EMP_LEAVE"
            ):
                for i in x["prjts"]:
                    if i not in d[x["Employee Number"]]:
                        d[x["Employee Number"]][i] = ["LEAVE"]
                    else:
                        d[x["Employee Number"]][i].append("LEAVE")
                if x["Employee Number"] in track_valid_projects_exclude_mt:
                    track_valid_projects_exclude_mt[x["Employee Number"]].append(True)

                else:
                    track_valid_projects_exclude_mt[x["Employee Number"]] = [True]
            elif (
                len(x["all_valid_projects"]) == 1
                and list(x["all_valid_projects"])[0] == "OUT_OF_RANGE"
            ):

                if x["Employee Number"] in track_valid_projects_exclude_mt:
                    track_valid_projects_exclude_mt[x["Employee Number"]].append(True)
                else:
                    track_valid_projects_exclude_mt[x["Employee Number"]] = [True]
            elif len(x["all_valid_projects"]) == 2:
                if (
                    list(x["all_valid_projects"])[0] == "OUT_OF_RANGE"
                    and list(x["all_valid_projects"])[1] == "EMP_LEAVE"
                ):

                    for i in x["prjts"]:
                        if i not in d[x["Employee Number"]]:
                            d[x["Employee Number"]][i] = ["LEAVE"]
                        else:
                            d[x["Employee Number"]][i].append("LEAVE")
                    if x["Employee Number"] in track_valid_projects_exclude_mt:
                        track_valid_projects_exclude_mt[x["Employee Number"]].append(
                            True
                        )
                    else:
                        track_valid_projects_exclude_mt[x["Employee Number"]] = [True]
                elif (
                    list(x["all_valid_projects"])[1] == "OUT_OF_RANGE"
                    and list(x["all_valid_projects"])[0] == "EMP_LEAVE"
                ):

                    for i in x["prjts"]:
                        if i not in d[x["Employee Number"]]:
                            d[x["Employee Number"]][i] = ["LEAVE"]
                        else:
                            d[x["Employee Number"]][i].append("LEAVE")
                    if x["Employee Number"] in track_valid_projects_exclude_mt:
                        track_valid_projects_exclude_mt[x["Employee Number"]].append(
                            True
                        )
                    else:
                        track_valid_projects_exclude_mt[x["Employee Number"]] = [True]
                else:
                    if x["Task"] in holidays:
                        for i in x["prjts"]:
                            d[x["Employee Number"]][i].append("LEAVE")
                    else:
                        for i in x["prjts"]:
                            d[x["Employee Number"]][i].append(False)

            else:
                if x["Task"] in holidays:
                    for i in x["prjts"]:
                        d[x["Employee Number"]][i].append("LEAVE")
                else:
                    for i in x["prjts"]:
                        d[x["Employee Number"]][i].append(False)

    track_valid_projects_exclude_mt_dict = {
        key: True if any(value) else False
        for key, value in track_valid_projects_exclude_mt.items()
    }

    new_valid_clients_df = pd.DataFrame(
        track_valid_projects_exclude_mt_dict.items(),
        columns=["Employee Number", "valid_exclude_mt"],
    )

    partial_result_merge = pd.merge(
        partial_result_merge, new_valid_clients_df, how="left"
    )

    partial_result_merge.drop(["validation"], axis=1, inplace=True)

    # rename column names for UI convenient and sort by date
    partial_result_merge = partial_result_merge.rename(
        index=str,
        columns=partial_result_merge_rename,
    ).sort_values("Date")

    def reformat(x):
        return {"columns": list(x[0].keys()), "data": [list(i.values()) for i in x]}

    # adjust the output for nested clients data for table simple formation
    partial_result_merge["Client data"] = partial_result_merge["0_x"].apply(
        lambda x: reformat(x)
    )
    partial_result_merge["validation"].fillna(False, inplace=True)
    capture_invalid_ids = []

    def revalidate(x):
        capture_status = []
        leave_case = 0
        if x in d:
            if bool(client_projects_only & set(d[x].keys())):
                for key, value in d[x].items():
                    if key in client_projects_only:
                        if True in value:
                            capture_status.append(True)

                        elif len(set(value)) == 1:
                            if value[0] == "LEAVE" or value[0] == "OUT_OF_RANGE":
                                capture_status.append(True)
                                leave_case += 1
                        elif len(set(value)) == 2:
                            if value[0] == "LEAVE" and value[1] == "OUT_OF_RANGE":
                                capture_status.append(True)
                                leave_case += 1
                            elif value[1] == "LEAVE" and value[0] == "OUT_OF_RANGE":
                                capture_status.append(True)
                                leave_case += 1
                else:
                    if not True in capture_status:
                        capture_invalid_ids.append(x)
            elif bool(internal_pocs_only & set(d[x].keys())):
                for key, value in d[x].items():
                    if key in internal_pocs_only:
                        if True in value:
                            capture_status.append(True)
                        elif len(set(value)) == 1:

                            if value[0] == "LEAVE" or value[0] == "OUT_OF_RANGE":
                                capture_status.append(True)
                        elif len(set(value)) == 2:

                            if value[0] == "LEAVE" and value[1] == "OUT_OF_RANGE":
                                capture_status.append(True)
                            elif value[1] == "LEAVE" and value[0] == "OUT_OF_RANGE":
                                capture_status.append(True)

                else:
                    if not True in capture_status:
                        capture_invalid_ids.append(x)

            if leave_case and leave_case >= len(capture_status):
                if bool(internal_pocs_only & set(d[x].keys())):
                    capture_status.clear()
                    for key, value in d[x].items():
                        if key in internal_pocs_only:
                            if True in value:
                                capture_status.append(True)
                            elif len(set(value)) == 1:
                                if value[0] == "LEAVE" or value[0] == "OUT_OF_RANGE":
                                    capture_status.append(True)
                            elif len(set(value)) == 2:
                                if value[0] == "LEAVE" and value[1] == "OUT_OF_RANGE":
                                    capture_status.append(True)
                                elif value[1] == "LEAVE" and value[0] == "OUT_OF_RANGE":
                                    capture_status.append(True)
                    else:
                        if not True in capture_status:
                            capture_invalid_ids.append(x)

    partial_result_merge["Employee Number"].drop_duplicates().apply(
        lambda x: revalidate(x)
    )
    partial_result_merge.loc[
        partial_result_merge["Employee Number"].isin(capture_invalid_ids), "validation"
    ] = False

    unsubmitted_rec = set(
        partial_result_merge[partial_result_merge["validation"] == True][
            "Employee Number"
        ].to_list()
    ).intersection(unsubmitted_employees)

    invalid_unsubmitted_rec = set(
        partial_result_merge[partial_result_merge["validation"] == False][
            "Employee Number"
        ].to_list()
    ).intersection(unsubmitted_employees)

    partial_result_merge.loc[
        partial_result_merge["Employee Number"].isin(unsubmitted_rec), "validation"
    ] = "Incomplete Hrs data"

    
    partial_result_merge['Comments'] = None
    # count the total invalid records
    invalid_data = partial_result_merge[partial_result_merge["validation"] == False]
    # Calculate counts for different validation statuses
    # invalid_count = len(pd.unique(partial_result_merge.loc[partial_result_merge["validation"] == False, "Employee Number"]))
    
    

    def project_and_billing_pulling(x):
        empty_string = ""
        for i in x["prjts"]:
            for j in x["0_x"]:
                if i == j["Project"]:
                    empty_string += i + ": " + j["Billing Status"] + ", "
        prjts_billing.append(empty_string)

    invalid_data.apply(lambda x: project_and_billing_pulling(x), axis=1)
    invalid_data["Assigned projects"] = prjts_billing
    
    invalid_data = invalid_data[
        [
            "Employee Number",
            "Employee Name",
            "Filled Project",
            "Task",
            "Filled Billing Type",
            "Status",
            "Date",
            "Assigned projects",
            "Comments"
        ]
    ].sort_values(by =["Employee Name", "Date"])
    invalid_data["Date"] = invalid_data["Date"].dt.strftime(date_format)
    # list out list of required columns
    partial_result_merge = partial_result_merge[partial_result_merge_columns]
    partial_result_merge.loc[
        partial_result_merge["validation"] == True, "validation"
    ] = "Satified"
    partial_result_merge.loc[
        partial_result_merge["validation"] == False, "validation"
    ] = "Incorrect submission"
    satisfied_count = len(pd.unique(partial_result_merge.loc[partial_result_merge["validation"] == "Satified", "Employee Number"]))
    incomplete_hours_count = len(pd.unique(partial_result_merge.loc[partial_result_merge["validation"] == "Incomplete Hrs data", "Employee Number"]))
    # incorrect_submission_count = len(pd.unique(partial_result_merge.loc[partial_result_merge["validation"] == "Incorrect submission", "Employee Number"]-invalid_count)) 
    partial_result_merge.loc[
        partial_result_merge["Employee Number"].isin(invalid_unsubmitted_rec),
        "validation"
    ] = "Invalid"
    invalid_count = len(pd.unique(partial_result_merge.loc[partial_result_merge["validation"] == "Invalid", "Employee Number"]))
    incorrect_submission_count = len(pd.unique(partial_result_merge.loc[partial_result_merge["validation"] == "Incorrect submission", "Employee Number"])) 
    partial_result_merge["Date"] = partial_result_merge["Date"].dt.strftime(date_format)

    return {'main_df': partial_result_merge, "logs_range": {
            "logs_start": sdt_date.strftime(date_format),
            "log_end": edt_date.strftime(date_format),
        }, "invalid_count": invalid_count,"satisfied_count":satisfied_count, "incorrect_submission_count": incorrect_submission_count, "incomplete_hours_count": incomplete_hours_count, "ivd_df": invalid_data.reset_index(drop=True)}
