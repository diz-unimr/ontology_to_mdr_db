from io import StringIO
from credentials import *
from functions import *
from requests.auth import HTTPBasicAuth

import pandas as pd
import requests


def get_data_from_xwiki(url_name):
    url = os.environ.get(url_name)
    username = os.environ.get('XWIKI_USERNAME')
    password = os.environ.get('XWIKI_PASSWORD')
    # Send a GET request with basic authentication to download the file
    response = requests.get(url, auth=HTTPBasicAuth(username, password))

    # Check if the request was successful
    if response.status_code == 200:
        df = pd.read_csv(StringIO(response.text))
        if url_name == 'XWIKI_ONTOLOGY_URL':
            column_mapping = {
                'Main.Metadatenrepository.Ontologien.Code.OntologienClass_CATEGORY': 'category',
                'Main.Metadatenrepository.Ontologien.Code.OntologienClass_BELONGS_TO': 'belongs_to',
                'Main.Metadatenrepository.Ontologien.Code.OntologienClass_TERMINOLOGY': 'terminology',
                'Main.Metadatenrepository.Ontologien.Code.OntologienClass_VERSION': 'version',
            }
        elif url_name == 'XWIKI_LABCODES_URL':
            column_mapping = {
                'Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_SWL_CODE': 'swl_code',
                'Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_SWL_DESCRIPTION': 'swl_description',
                'Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_SWL_UNIT': 'swl_unit',
                'Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_BELONGS_TO': 'belongs_to',
                'Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_SWL_METACODE': 'swl_metacode',
                'Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_CODE': 'code',
                'Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_CODE_LONG_NAME': 'code_long_name',
                'Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_CODE_SYSTEM': 'code_system',
                'Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_VERSION': 'version',
                'Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_UCUM_UNIT': 'ucum_unit',
                'Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_VALIDATED': 'validated',
            }
        # Filter the DataFrame to include only columns specified in the column mapping
        df_columns = df.columns.tolist()
        df = df[df_columns].copy()
        df.rename(columns=column_mapping, inplace=True)
        df.reset_index(drop=True, inplace=True)
        df.columns = df.columns.str.lower()
        return df
    else:
        print('Failed to download file. Status code:', response.status_code)
        return None

def create_ontology_table():
    ontologies = get_data_from_xwiki('XWIKI_ONTOLOGY_URL')
    ontologies = ontologies[ontologies['belongs_to'] != 'AppWithinMinutes.DBList']

    columns = ['id', 'module_id', 'parent_id', 'display', 'term_codes', 'selectable', 'leaf', 'time_restriction_allowed', 'filter_type', 'filter_options', 'version']
    df = pd.DataFrame(columns=columns)
    df.to_csv('ontology_table.csv', index=False, mode='w')  # Create file with headers
    ontology_table = pd.DataFrame(columns=columns)

    module_id = find_module_id('Laboruntersuchung')
    # sorting ontology from parent to children
    ontologies_level1 = ontologies[ontologies['belongs_to'] == 'Laboruntersuchung']
    ontologies_level2 = ontologies[ontologies['belongs_to'].isin(ontologies_level1['category'].to_list())]
    ontologies_level3 = ontologies[~ontologies['category'].isin(ontologies_level1['category'].to_list() + ontologies_level2['category'].to_list())]
    ontologies = pd.concat([ontologies_level1, ontologies_level2, ontologies_level3], ignore_index=True)

    for _, ontology in ontologies.iterrows():
        if ontology['belongs_to'] == 'Laboruntersuchung':
            parent_id = None
        else:
            parent_id = df[df['display'] == ontology['belongs_to']]['id'].values[0]
        id = hashlib.md5(f"{module_id}{ontology['category']}{ontology['belongs_to']}{ontology['version']}".encode()).hexdigest()
        data = pd.DataFrame([{
            'id': id,
            'module_id': module_id,
            'parent_id': parent_id,
            'display': ontology['category'],
            'term_codes': None,
            'selectable': False,
            'leaf': False,
            'time_restriction_allowed': None,
            'filter_type': None,
            'filter_options': None,
            'version': '2.2.0'
        }])
        df = pd.concat([df, data], ignore_index=True)
    df.to_csv('kds_concepts.csv', index=False, mode='a', header=False)
    return df


def create_lab_codes_concepts_table(ontology_table):
    lab_codes = get_data_from_xwiki('XWIKI_LABCODES_URL')
    lab_codes = lab_codes[lab_codes['swl_metacode'] != 'X']
    
    csv_filename = 'kds_concepts.csv'
    columns = ['id', 'module_id', 'parent_id', 'display', 'term_codes', 'selectable', 'leaf', 'time_restriction_allowed', 'filter_type', 'filter_options', 'version']
    df = pd.DataFrame(columns=columns)
    df.to_csv(csv_filename, index=False, mode='w')  # Create file with headers

    # ui_profile = read_json_file(['ontology/ui_profile.json'])[0]
    # profile_filter = ui_profile['Laboruntersuchung']
    module_id = find_module_id('Laboruntersuchung')
    term_codes = []

    for i in range(len(lab_codes)):
        swl_code = lab_codes.iloc[i]['swl_code']
        loinc = lab_codes.iloc[i]['code']
        term_code = {
            'code': lab_codes.iloc[i]['code'],
            'display': lab_codes.iloc[i]['code_long_name'],
            'system': lab_codes.iloc[i]['code_system'],
            'version': lab_codes.iloc[i]['version']
        }
        term_codes.append(term_code)

        try:
            condition_met = swl_code != lab_codes.iloc[i+1]['swl_code']
        except:
            condition_met = i == len(lab_codes)-1

        if condition_met:
            id = hashlib.md5(f"{module_id}{swl_code}{loinc}{term_codes}".encode()).hexdigest()
            try: parent_id = ontology_table[ontology_table['display'] == lab_codes.iloc[i]['belongs_to']]['id'].values[0]
            except: parent_id = None

            df = pd.DataFrame([{
                'id': id,
                'module_id': module_id,
                'parent_id': parent_id,
                'display': lab_codes.iloc[i]['swl_description'],
                'term_codes': json.dumps(term_codes),
                'selectable': True,
                'leaf': True,
                'time_restriction_allowed': True,
                'filter_type': None,
                'filter_options': None,
                'version': '2.2.0'
            }])
            term_codes = []
            df.to_csv(csv_filename, encoding='utf-8', index=False, mode='a', header=False)
