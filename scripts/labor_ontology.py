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
                'Main.Metadatenrepository.Ontologien.Code.OntologienClass_VERSION': 'version',
            }
        elif url_name == 'XWIKI_LABCODES_URL':
            column_mapping = {
                'Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_SWL_CODE': 'swl_code',
                'Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_SWL_DESCRIPTION': 'swl_description',
                'Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_SWL_UNIT': 'swl_unit',
                'Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_BELONGS_TO': 'belongs_to',
                'Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_SWL_METACODE': 'swl_metacode',
                'Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_SWL_SOURCE': 'swl_source',
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

def check_csv_file_exist(csv_filename):
    # Check if the file exists
    if os.path.exists(csv_filename):
        print("The file exists.")
    else:
        print("The file does not exist.")
        columns = ['id', 'module_id', 'parent_id', 'display', 'term_codes', 'selectable', 'leaf', 'time_restriction_allowed', 'filter_type', 'filter_options', 'version']
        df = pd.DataFrame(columns=columns)
        df.to_csv(csv_filename, index=False, mode='w')  # Create file with headers

def create_ontology_table():
    ontologies = get_data_from_xwiki('XWIKI_ONTOLOGY_URL')
    ontologies = ontologies[ontologies['belongs_to'] != 'AppWithinMinutes.DBList']

    check_csv_file_exist('concepts.csv')

    module_id = find_module_id('Laboruntersuchung')
    # sorting ontology from parent to children
    ontologies_level1 = ontologies[ontologies['belongs_to'] == 'Laboruntersuchung']
    ontologies_level2 = ontologies[ontologies['belongs_to'].isin(ontologies_level1['category'].to_list())]
    ontologies_level3 = ontologies[~ontologies['category'].isin(ontologies_level1['category'].to_list() + ontologies_level2['category'].to_list())]
    ontologies = pd.concat([ontologies_level1, ontologies_level2, ontologies_level3], ignore_index=True)
    
    df = pd.DataFrame()
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
    df.to_csv('concepts.csv', index=False, mode='a', header=False)
    return df

def create_lab_codes_concepts_table(ontology_table):
    # get lab codes from xwiki 
    lab_codes = get_data_from_xwiki('XWIKI_LABCODES_URL')
    lab_codes = lab_codes[lab_codes['swl_metacode'] != 'X']
    lab_codes = lab_codes[lab_codes['code_system'] != 'http://snomed.org']
    lab_codes.to_csv('lab_codes.csv')

    check_csv_file_exist('concepts.csv')

    module_id = find_module_id('Laboruntersuchung')
    term_codes = []
    df_temp = pd.DataFrame()

    for i in range(len(lab_codes)):
        term_codes_child = []
        is_selectable = True
        swl_code = str(lab_codes.iloc[i]['swl_code']).strip()
        loinc = str(lab_codes.iloc[i]['code']).strip()
        child_id = hashlib.md5(f"{module_id}{swl_code}{loinc}{term_codes}".encode()).hexdigest()
        # term_codes with swisslab code
        swl_term_code = {
            'code': swl_code,
            'display': str(lab_codes.iloc[i]['swl_description']).strip(),
            'system': 'https://fhir.diz.uni-marburg.de/CodeSystem/swisslab-code',
            'version': ''
        }
        term_codes_child.append(swl_term_code)
        term_codes.append(swl_term_code) if swl_code not in {item['code'] for item in term_codes} else None

        # term_codes with loinc
        if lab_codes.iloc[i]['validated'] == 'X' and lab_codes.iloc[i]['code_system'] == 'http://loinc.org':
            loinc_term_code = {
                'code': loinc,
                'display': str(lab_codes.iloc[i]['code_long_name']).strip() if lab_codes.iloc[i]['code_long_name'] else str(lab_codes.iloc[i]['swl_description']).strip(),
                'system': 'http://loinc.org',
                'version': str(lab_codes.iloc[i]['version']).strip()
            }
            term_codes_child.append(loinc_term_code)
            term_codes.append(loinc_term_code) if loinc not in {item['code'] for item in term_codes} else None

        if not 'loin' in str(term_codes_child):
            warningText = ' (Die Suche nach SWL-Code wird momentan nicht unterstützt)'
            is_selectable = False
        else:
            warningText = ''
            is_selectable = True

        df = pd.DataFrame([{
                'id': child_id,
                'module_id': module_id,
                'parent_id': None,
                'display': str(lab_codes.iloc[i]['swl_description']).strip()  + ( ' (' + str(lab_codes.iloc[i]['swl_source']).strip() + ')' if lab_codes.iloc[i]['swl_source'] else '') + str(warningText),
                'term_codes': json.dumps(term_codes_child),
                'selectable': is_selectable,
                'leaf': True,
                'time_restriction_allowed': True,
                'filter_type': None,
                'filter_options': None,
                'version': '2.2.0'
            }])
        df_temp = pd.concat([df_temp, df], ignore_index=True)

        try:
            condition_met = swl_code != lab_codes.iloc[i+1]['swl_code'] # and lab_codes.iloc[i]['swl_description'] != lab_codes.iloc[i+1]['swl_description']
        except:
            condition_met = i == len(lab_codes)-1

        if condition_met:
            id = hashlib.md5(f"{module_id}{swl_code}{loinc}{term_codes}".encode()).hexdigest()
            try: parent_id = ontology_table[ontology_table['display'] == lab_codes.iloc[i]['belongs_to']]['id'].values[0]
            except: parent_id = None
            if not 'loin' in str(term_codes):
                warningText = ' (Die Suche nach SWL-Code wird momentan nicht unterstützt)'
                is_selectable = False
            else: 
                warningText = ''
                is_selectable = True
            
            df = pd.DataFrame([{
                'id': id,
                'module_id': module_id,
                'parent_id': parent_id,
                'display': str(lab_codes.iloc[i]['swl_code']).strip() if (not lab_codes.iloc[i]['swl_description']) or lab_codes.iloc[i]['swl_description'] == 'emptyvalue' else str(lab_codes.iloc[i]['swl_description']).strip() + str(warningText),
                'term_codes': json.dumps(term_codes),
                'selectable': is_selectable,
                'leaf': True,
                'time_restriction_allowed': True,
                'filter_type': None,
                'filter_options': None,
                'version': '2.2.0'
            }])

            if not 'loin' in df['term_codes']:
                warningText = 'Die Suche nach SWL-Code wird momentan nicht unterstützt'

            term_codes = []
            df.to_csv('concepts.csv', encoding='utf-8', index=False, mode='a', header=False)
            if not df['term_codes'].equals(df_temp['term_codes']):
                df_temp['parent_id'] = id
                df_temp.to_csv('concepts.csv', encoding='utf-8', index=False, mode='a', header=False)
            df_temp = pd.DataFrame()

def check_lab():
    df = pd.read_csv('lab_codes.csv')
    duplicates = df[df.duplicated(subset=['swl_description', 'code'], keep=False)]
    print(duplicates)