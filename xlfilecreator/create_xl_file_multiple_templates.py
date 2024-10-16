import pandas as pd
import xlsxwriter
from tqdm.auto import tqdm 

import datetime
import os
import shutil
from typing import Optional, List

from .conditional_formatting import highlight_mandatory
from .create_xlfile import process_template, protect_workbook
from .encrypt_xl import set_password, create_password
from .header_format import set_headers_format
from .utils_func import (set_project_name, create_output_folders)
from .xlfiletemp import XlFileTemp


def create_xl_file_multiple_temp(*, project_name: str, template_list: List[XlFileTemp], split_by_value: bool, split_by: Optional[str]=None, 
    split_by_range: Optional[List[str]]=None, batch: Optional[int]=1, sheet_password: Optional[str]=None, workbook_password: Optional[str]=None,
    protect_files: Optional[bool]=False, random_password: Optional[bool]=False, in_zip: Optional[bool]=False) -> None:
    """
    Creates the Excel file with multiple tamples in it.

    project_name: name of the project, it will be part of the filename of the templates. If split_by is None it will be the name of the single file generated
    template_list: Python list containing the templates (XlFileTemp objects) to include in the Excel File.
    split_by_value: A boolean flag (True or False). If True, the method filters by the split_value provided. If False, it uses all values from the split_by column.
    split_by: The name of the column to filter by.
    split_by_range: Python list contaning all the split_value items. If split_by_value=True All split_value items must be included in all templates provided.
    batch: Number of the batch. Included in the filename of the templates.
    sheet_password: sheet password for the excel file to avoid the users to change the format of the main sheet, default=None 
    workbook_password: workbook password to avoid the users to add more sheets in the excel file, defaul=None
    protect_files: False/True encrypt the files
    random_password: False/True if protect_files is True it determines if the password of the files should be random or based on a logic
    in_zip: False/True Download folders in zip
    """

    if split_by is None and split_by_range is None:
        return None

    if isinstance(split_by_range, list):
        values_to_split = set(split_by_range)
    else:
        raise TypeError(f'{split_by_range} is not a list')

    ### Check feasibility
    if split_by_value:
        for template in template_list:
            print(f"Checking: {template.tab_names['main_sheet']}")
            template.check_split_by_range(split_by, split_by_range)

    ### Create output folders
    today = datetime.datetime.today().strftime('%Y%m%d')
    project = set_project_name(project_name)
    path_1, path_2 = create_output_folders(project.name, today, protect_files)
    
    ### 
    password_master = []
    pbar = tqdm(total=len(values_to_split))
    for i, split_value in enumerate(values_to_split, 1):
        ### Remove special characters from the supplier name
        name = ''.join(char for char in split_value if char == ' ' or char.isalnum())
        id_file = f'{project.name}ID{batch}{i:03d}'
        file_name = f'{id_file}-{name}-{today}.xlsx'
        file_path = f'{path_1}/{file_name}'
        
        ### Create Excel file
        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:

            for j, template in enumerate(template_list, 1):
                template_name = f'Sheet{j}'
                process_template(writer, template, split_by_value, template_name, split_by, split_value, sheet_password)
                
        ### Protect Workbook
        if workbook_password is not None and workbook_password != '':
            protect_workbook(file_path, password=workbook_password)

        ### Create Password master df
        if protect_files is True:
            pw = create_password(project, split_value, random_password)    
            password_master.append((id_file, file_name, split_value, pw))

    ### Encrypt Excel files
    if protect_files is True:
        df_pw = pd.DataFrame(password_master, columns=['File ID', 'Filename', split_by, 'Password'])
        passwordMaster_name = f'{project.name}-PasswordMaster-{today}.csv'
        df_pw.to_csv(passwordMaster_name, index=False)

        set_password(path_1, path_2, passwordMaster_name)
        print(df_pw)

    pbar.close()

    if in_zip:
        shutil.make_archive(path_1, 'zip', path_1)
        shutil.make_archive(path_2, 'zip', path_2)
        os.system(f'rm -r {path_1}')
        os.system(f'rm -r {path_2}')
