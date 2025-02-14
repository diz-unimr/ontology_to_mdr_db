from credentials import *
import json
import pandas as pd
import psycopg2
import hashlib
from psycopg2.extensions import connection  # Import connection type
from typing import List, Tuple, Dict, Union

JSONType = Dict[str, Union[str, int, float, bool, None, List["JSONType"], Dict[str, "JSONType"]]]


def read_json_file(urls: List[str]) -> List[JSONType]:
    json_data = []
    for url in urls:
        with open(url, encoding="utf-8") as file:
            json_file = json.load(file)
            json_data.append(json_file)
    return json_data

def create_kds_beschreibung_table(ontology_trees: List[JSONType]) -> None:
    csv_filename = "kds_beschreibung.csv"
    columns = ["id", "kds_module_name", "fdpg_kds_code", "fdpg_kds_system", "fdpg_kds_version", "version"]
    
    df = pd.DataFrame(columns=columns)
    df.to_csv(csv_filename, index=False, mode="w")  # Create file with headers

    for object in ontology_trees:
        id = hashlib.md5(f"{object['children'][0]['context']['code']}{object['children'][0]['context']['system']}{object['children'][0]['context']['version']}{'2.2.0'}".encode()).hexdigest()
        df = pd.DataFrame([{
            "id": id,
            "kds_module_name": object['context']['display'],
            "fdpg_kds_code": object['children'][0]['context']['code'],
            "fdpg_kds_system": object['children'][0]['context']['system'],
            "fdpg_kds_version": object['children'][0]['context']['version'],
            "version": "2.2.0"
        }])
        df.to_csv(csv_filename, index=False, mode="a", header=False) # Append to the CSV file

def find_module_id(context_code: str):
    kds_beschreibung = pd.read_csv('kds_beschreibung.csv')
    id = kds_beschreibung[kds_beschreibung["fdpg_kds_code"] == context_code]['id'].values[0]
    return id if len(id) > 0 else None

def traverse_children(ontology: List[JSONType], profile_filter: Union[JSONType, None], parent_id: Union[str, None], csv_filename):
    module_id = find_module_id(ontology[0]['context']['code'])

    for node in ontology:
        id = hashlib.md5(f"{module_id}{node['termCodes'][0]}".encode()).hexdigest()
        if node['context']['code'] != "Procedure" and node['context']['code'] != "Diagnose":
            profile_filter = get_profile_filter(node)
        print(module_id)
        df = pd.DataFrame([{
            "id": id,
            "module_id": module_id,
            "parent_id": parent_id,
            "display": node['display'],
            "term_codes": json.dumps(node['termCodes']),
            "selectable": node['selectable'],
            "leaf": node['leaf'],
            "time_restriction_allowed": profile_filter['timeRestrictionAllowed'],
            "filter_type": profile_filter['valueDefinition']['type'] if profile_filter['valueDefinition'] is not None else None,
            "filter_options": json.dumps(profile_filter['valueDefinition']['allowedUnits']) if profile_filter['valueDefinition'] and profile_filter['valueDefinition']['allowedUnits'] != [] else json.dumps(profile_filter['valueDefinition']['selectableConcepts']) if profile_filter['valueDefinition'] and profile_filter['valueDefinition']['selectableConcepts'] != [] else None,
            "version": '2.2.0'
        }])

        df.to_csv(csv_filename, index=False, mode="a", header=False)

        if 'children' in node:
            traverse_children(ontology=node['children'], profile_filter=profile_filter, parent_id=id, csv_filename=csv_filename)

def get_profile_filter(ontology: JSONType) -> Union[JSONType, None]:
    ui_profile = read_json_file(['ontology/ui_profile.json'])[0]
    try:
        profile_filter = ui_profile[ontology['display']]
    except: 
        profile_filter = None
    return profile_filter

def create_kds_concepts_table(ontology_trees: List[JSONType]) -> None:
    csv_filename = "kds_concepts.csv"
    columns = ["id", "module_id", "parent_id", "display", "term_codes", "selectable", "leaf", "time_restriction_allowed", "filter_type", "filter_options", "version"]
    df = pd.DataFrame(columns=columns)
    df.to_csv(csv_filename, index=False, mode="w")  # Create file with headers
    
    for ontology in ontology_trees:
        profile_filter = get_profile_filter(ontology)
        traverse_children(ontology=ontology['children'], profile_filter=profile_filter, parent_id=None, csv_filename=csv_filename)

def connect_db() -> connection:
    # Connect to the MDR database
    global conn
    try: 
        conn = psycopg2.connect(
            host=os.environ.get("MDR_HOST"),
            port=os.environ.get("MDR_PORT"),
            database=os.environ.get("MDR_DATABASE"),
            user=os.environ.get("MDR_USERNAME"),
            password=os.environ.get("MDR_HOST")
        )
        return conn
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        return None

def close_db():
    global conn
    if conn is not None:
        conn.close()
        conn = None