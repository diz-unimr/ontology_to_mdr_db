from io import StringIO
from credentials import *
from functions import *
from requests.auth import HTTPBasicAuth
from mapping import *

import pandas as pd
import requests


def get_data_from_xwiki(url_name):
    url = os.environ.get(url_name)
    username = os.environ.get("XWIKI_USERNAME")
    password = os.environ.get("XWIKI_PASSWORD")
    # Send a GET request with basic authentication to download the file
    response = requests.get(url, auth=HTTPBasicAuth(username, password))
    # Check if the request was successful
    if response.status_code == 200:
        df = pd.read_csv(StringIO(response.text), encoding="utf-8", keep_default_na=False)
        if url_name == "XWIKI_ONTOLOGY_URL":
            column_mapping = {
                "Main.Metadatenrepository.Ontologien.Code.OntologienClass_CATEGORY": "category",
                "Main.Metadatenrepository.Ontologien.Code.OntologienClass_BELONGS_TO": "belongs_to",
                "Main.Metadatenrepository.Ontologien.Code.OntologienClass_VERSION": "version",
            }
        elif url_name == "XWIKI_LABCODES_URL":
            column_mapping = {
                "Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_SWL_CODE": "swl_code",
                "Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_SWL_DESCRIPTION": "swl_description",
                "Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_SWL_UNIT": "swl_unit",
                "Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_BELONGS_TO": "belongs_to",
                "Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_SWL_METACODE": "swl_metacode",
                "Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_SWL_SOURCE": "swl_source",
                "Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_CODE": "code",
                "Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_CODE_LONG_NAME": "code_long_name",
                "Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_CODE_SYSTEM": "code_system",
                "Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_VERSION": "version",
                "Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_UCUM_UNIT": "ucum_unit",
                "Main.Metadatenrepository.Laborcodes.Code.LaborcodesClass_VALIDATED": "validated",
            }
        # Filter the DataFrame to include only columns specified in the column mapping
        
        df_columns = df.columns.tolist()
        df = df[df_columns].copy()
        df.rename(columns=column_mapping, inplace=True)
        df.reset_index(drop=True, inplace=True)
        df.columns = df.columns.str.lower()
        return df
    else:
        print("Failed to download file. Status code:", response.status_code)
        return None

def check_csv_file_exist(csv_filename):
    # Check if the file exists
    if os.path.exists(csv_filename):
        print("The file exists.")
    else:
        print("The file does not exist.")
        columns = ["id", "module_id", "parent_id", "display", "term_codes", "selectable", "leaf", "time_restriction_allowed", "filter_type", "filter_options", "version"]
        df = pd.DataFrame(columns=columns)
        df.to_csv(csv_filename, index=False, mode="w")  # Create file with headers

def create_ontology_table():
    ontologies = get_data_from_xwiki("XWIKI_ONTOLOGY_URL")
    ontologies = ontologies[ontologies["belongs_to"] != "AppWithinMinutes.DBList"]

    check_csv_file_exist("concepts.csv")

    module_id = find_module_id("Laboruntersuchung")
    # sorting ontology from parent to children
    ontologies_level1 = ontologies[ontologies["belongs_to"] == "Laboruntersuchung"]
    ontologies_level2 = ontologies[ontologies["belongs_to"].isin(ontologies_level1["category"].to_list())]
    ontologies_level3 = ontologies[~ontologies["category"].isin(ontologies_level1["category"].to_list() + ontologies_level2["category"].to_list())]
    ontologies = pd.concat([ontologies_level1, ontologies_level2, ontologies_level3], ignore_index=True)
    
    df = pd.DataFrame()
    for _, ontology in ontologies.iterrows():
        if ontology["belongs_to"] == "Laboruntersuchung":
            parent_id = None
        else:
            parent_id = df[df["display"] == ontology["belongs_to"]]["id"].values[0]
            
        id = hashlib.md5(f"{module_id}{ontology['category']}{ontology['belongs_to']}{ontology['version']}".encode()).hexdigest()
        data = pd.DataFrame([{
            "id": id,
            "module_id": module_id,
            "parent_id": parent_id,
            "display": ontology["category"],
            "term_codes": None,
            "selectable": False,
            "leaf": False,
            "time_restriction_allowed": None,
            "filter_type": None,
            "filter_options": None,
            "version": "2.2.0"
        }])
        df = pd.concat([df, data], ignore_index=True)
    df.to_csv("concepts.csv", index=False, mode="a", header=False)
    return ontologies

def create_lab_codes_concepts_table():
    ontology_table = pd.read_csv("concepts.csv")
    # get lab codes from xwiki 
    lab_codes = get_data_from_xwiki("XWIKI_LABCODES_URL")
    lab_codes = lab_codes[lab_codes["swl_metacode"] != "X"]
    lab_codes = lab_codes[lab_codes["code_system"] != "http://snomed.org"]
    lab_codes.to_csv("xwiki_lab_codes.csv")
    module_id = find_module_id("Laboruntersuchung")

    check_csv_file_exist("concepts.csv")
    
    for i in range(len(lab_codes)):
        term_codes = []
        swl_code = str(lab_codes.iloc[i]["swl_code"]).strip()
        swl_display = str(lab_codes.iloc[i]["swl_description"]).strip()
        loinc = str(lab_codes.iloc[i]["code"]).strip()
        loinc_display = str(lab_codes.iloc[i]["code_long_name"]).strip() if lab_codes.iloc[i]["code_long_name"] else swl_display
        mapping_fhir_new = create_labor_mapping_fhir(swl_code, swl_display, loinc, loinc_display)
        
        # get parent id from ontology table
        try:
            parent_id = ontology_table[ontology_table["display"] == lab_codes.iloc[i]["belongs_to"]]["id"].values[0]
        except:
            parent_id = None
            
        # term_codes with swisslab code
        swl_term_code = {
            "code": swl_code,
            "display": str(lab_codes.iloc[i]["swl_description"]).strip(),
            "system": "https://fhir.diz.uni-marburg.de/CodeSystem/swisslab-code",
        }
        term_codes.append(swl_term_code)

        # term_codes with loinc
        if lab_codes.iloc[i]["validated"] == "X" and lab_codes.iloc[i]["code_system"] == "http://loinc.org":
            loinc_term_code = {
                "code": loinc,
                "display": str(lab_codes.iloc[i]["code_long_name"]).strip() if lab_codes.iloc[i]["code_long_name"] else str(lab_codes.iloc[i]["swl_description"]).strip(),
                "system": "http://loinc.org",
                "version": str(lab_codes.iloc[i]["version"]).strip()
            }
            term_codes.append(loinc_term_code)

        df = pd.DataFrame([{
                "id": hashlib.md5(f"{module_id}{swl_code}{loinc}{term_codes}".encode()).hexdigest(),
                "module_id": module_id,
                "parent_id": parent_id,
                "display": str(lab_codes.iloc[i]["swl_description"]).strip()  + ( " (" + str(lab_codes.iloc[i]["swl_source"]).strip() + ")" if lab_codes.iloc[i]["swl_source"] and (lab_codes.iloc[i]["swl_source"] != "emptyvalue" and lab_codes.iloc[i]["swl_source"] != "") else ""),
                "term_codes": json.dumps(term_codes, ensure_ascii=False),
                "selectable": True,
                "leaf": True,
                "time_restriction_allowed": True,
                "filter_type": None,
                "filter_options": None,
                "version": "2.2.0"
            }])

        df.to_csv("concepts.csv", encoding="utf-8", index=False, mode="a", header=False)
        
    with open("mapping_fhir_new_lab2.json", "w", encoding="utf-8") as f:
            json.dump(mapping_fhir_new, f, ensure_ascii=False, indent=2)

def check_lab():
    df = pd.read_csv("xwiki_lab_codes.csv")
    duplicates = df[df.duplicated(subset=["swl_description", "code"], keep=False)]
    print(duplicates)

def check_duplicate():
    df = pd.read_csv("concepts.csv")
    duplicates = df[df.duplicated("id", keep=False)]
    print(duplicates)