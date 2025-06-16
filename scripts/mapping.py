"""
    SPDX-FileCopyrightText: Nattika Jugkaeo <nattika.jugkaeo@uni-marburg.de>
    SPDX-License-Identifier: AGPL-3.0-or-later
"""
from __future__ import annotations
from functions import read_json_file
import pandas as pd
import json
import requests
from typing import TypedDict, List, Dict, Union, Optional


class TermCodes(TypedDict):
    code: str
    system: str
    display: str
    version: str

class Context(TypedDict):
    code: str
    system: str
    version: str
    display: str

class FilterOptions(TypedDict):
        code: str
        display: str
        system: Optional[str]
        version: Optional[str]

class Criterion(TypedDict):
    children: List[Criterion]
    id: str
    moduleId: str
    parentId: Optional[str]  # string or none (null)
    display: str
    termCodes: List[TermCodes]
    context: Optional[Context]
    selectable: bool
    leaf: bool
    timeRestrictionAllowed: Optional[bool]
    filterOptions: Optional[List[FilterOptions]]
    filterType: Optional[str]
    version: str

class MappingTree(TypedDict):
    children: Optional[List[MappingTree]]
    context: Context
    termCode: TermCodes


with open("mapping_template/mapping_fhir.json", "r", encoding="utf-8") as f:
    mapping_fhir2 = json.load(f)

with open("mapping_template/mapping_tree.json", "r", encoding="utf-8") as f:
    mapping_tree2 = json.load(f)

def get_request(url: str, default_na: bool) -> List[Dict]:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()  # parse JSON directly to Python list/dict
        return data

def create_labor_mapping_fhir(swl_code: str, swl_display:str, loinc: str, loinc_display: str) -> None:
    [mapping_fhir] = read_json_file(["mapping_template/mapping_fhir.json"])
    # check if loinc/swl code already exists
    is_loinc_exists = any(entry.get("key", {}).get("code") == loinc for entry in mapping_fhir)
    is_swl_exists = any(entry.get("key", {}).get("code") == loinc for entry in mapping_fhir)

    if not is_loinc_exists:
        mapping = {
            "context": {
                "code": "Laboruntersuchung",
                "display": "Laboruntersuchung",
                "system": "fdpg.mii.cds",
                "version": "1.0.0"
            },
            "fhirResourceType": "Observation",
            "key": {
                "code": loinc,
                "display": loinc_display,
                "system": "http://loinc.org",
            },
            "name": "QuantityObservation",
            "termCodeSearchParameter": "code",
            "timeRestrictionParameter": "date"
        }
        mapping_fhir.append(mapping)
        
    if not is_swl_exists:
        mapping = {
            "context": {
                "code": "Laboruntersuchung",
                "display": "Laboruntersuchung",
                "system": "fdpg.mii.cds",
                "version": "1.0.0"
            },
            "fhirResourceType": "Observation",
            "key": {
                "code": swl_code,
                "display": swl_display,
                "system": "http://fhir.diz.uni-marburg.de/CodeSystem/swisslab-code",
            },
            "name": "QuantityObservation",
            "termCodeSearchParameter": "code",
            "timeRestrictionParameter": "date"
        }
        mapping_fhir.append(mapping)

    if not is_loinc_exists or not is_swl_exists:
        with open("mapping_fhir_new_lab.json", "w", encoding="utf-8") as f:
            json.dump(mapping_fhir, f, ensure_ascii=False, indent=2)
    return mapping_fhir


def create_categories_node(lab_categories, context, mapping_tree_labor):
    # add category(parent) node first (lab_categories is arranged in order of category/node level)
    for index, category in lab_categories.iterrows():
        category_node = {
            "children": [],
            "context": context,
            "termCode": {
                "code": category["category"],
                "display": category["category"],
                "system": context["system"],
                "version": category["version"]
            }
        }

        # add category in first level (under Laboruntersuchung)
        if category["belongs_to"] == "Laboruntersuchung":
            mapping_tree_labor["children"].append(category_node)
        # add category in second level
        else:
            parent_node: MappingTree = next((node for node in mapping_tree_labor["children"] if node["termCode"]["code"] == category["belongs_to"]))
            if (parent_node):
                parent_node["children"].append(category_node)
    return mapping_tree_labor


def create_labor_mapping_tree(lab_categories):
    modules = get_request("https://mdr.diz.uni-marburg.de/api/ontology/modules", True)
    lab_codes = pd.read_csv("xwiki_lab_codes.csv")
    [mapping_tree] = read_json_file(["mapping_template/mapping_tree.json"])
    module_labor = next((module for module in modules if module["name"] == "Laboruntersuchung"), None) 
    
    context: Context = {
        "code": module_labor["name"],
        "display": module_labor["name"],
        "system": module_labor["fdpg_cds_system"],
        "version": module_labor["fdpg_cds_version"]
    }
    # start template
    mapping_tree_labor: MappingTree = {
        "children": [],
        "context": context,
        "termCode": context
    }

    mapping_tree_labor = create_categories_node(lab_categories, context, mapping_tree_labor)

    # add lab node in their parent
    for index, lab_code in lab_codes.iterrows():
        print(lab_code["code"], lab_code["swl_code"])
        swl_code = str(lab_code["swl_code"]).strip() if str(lab_code["swl_code"]).strip() != 'emptyvalue' else None
        display_swl = lab_code["swl_description"].strip() if lab_code["swl_description"].strip() != 'emptyvalue' else None
        loinc = str(lab_code["code"]).strip() if str(lab_code["code"]).strip() != 'emptyvalue' else None
        display_loinc = lab_code["code_long_name"].strip() if lab_code["code_long_name"] else None
        version_loinc = str(lab_code["version"]).strip() if str(lab_code["version"]).strip() != 'emptyvalue' else ""
        belongs_to = str(lab_code["belongs_to"]).strip() if lab_code["belongs_to"] else None
        found_parent = False
        
        new_loinc_node = {
            "context": context,
            "termCode": {
                "code": loinc,
                "display": display_loinc,
                "system": "http://loinc.org",
                "version": version_loinc
            },
        }

        new_swl_node = {
            "context": {
                "code": "Laboruntersuchung",
                "display": "Laboruntersuchung",
                "system": "fdpg.mii.cds",
                "version": "1.0.0"
            },
            "termCode": {
                "code": swl_code,
                "display": display_swl,
                "system": "https://fhir.diz.uni-marburg.de/CodeSystem/swisslab-code",
                "version": ""
            },
        }

        queue = [mapping_tree_labor]
        #queue = [next((item for item in mapping_tree["children"] if item["context"]["code"] == "Laboruntersuchung"), None)]
        # no parent
        if not belongs_to or belongs_to == "emptyvalue" or belongs_to == "#NV" or belongs_to == "#REF!":
            if (loinc):
                queue[0]["children"].append(new_loinc_node)
            if (swl_code):
                queue[0]["children"].append(new_swl_node)
            continue

        # Breadth-First Search (BFS) with while and pop
        while queue:
            current_node = queue.pop(0)
            if belongs_to == current_node["termCode"]["code"]:
                # Create a new node
                if (loinc and loinc != "emptyvalue"):
                    current_node.setdefault("children", []).append(new_loinc_node)
                if (swl_code and swl_code != "emptyvalue"):
                    current_node.setdefault("children", []).append(new_swl_node)
                found_parent = True
                break

            # add elements to the end of queue
            if "children" in current_node and len(current_node["children"]) > 0:
                queue.extend(current_node["children"])

        if not found_parent:
            if (loinc or swl_code):
                # create new category node
                category_node = {
                    "children": [],
                    "context": context,
                    "termCode": {
                        "code": belongs_to,
                        "display": belongs_to,
                        "system": context["system"],
                        "version": ""
                    }
                }
                if (loinc):
                    category_node["children"].append(new_loinc_node)
                if (swl_code):
                    category_node["children"].append(new_swl_node)
                mapping_tree_labor["children"].append(category_node)

    with open("mapping_tree_lab.json", "w", encoding="utf-8") as f:
        json.dump(mapping_tree_labor, f, ensure_ascii=False, indent=2)

    # append mapping_tree_labor into orginal template
    mapping_tree["children"].append(mapping_tree_labor)
    with open("mapping_tree_for_machbarkeit.json", "w", encoding="utf-8") as f:
        json.dump(mapping_tree, f, ensure_ascii=False, indent=2)
        

def insert_node_to_mapping_tree():
    [mapping_tree] = read_json_file(["mapping_template/mapping_tree.json"])
    lab_codes = pd.read_csv("xwiki_lab_codes.csv")
    for index, lab in lab_codes.iterrows():
        queue = [next((item for item in mapping_tree["children"] if item["context"]["code"] == "Laboruntersuchung"), None)]
        swl_code = str(lab["swl_code"]).strip()
        loinc = str(lab["code"]).strip()
        belong_to = str(lab["belongs_to"]).strip() if lab["belongs_to"] else "emptyvalue"

        found_parent = False
        new_loinc_node = {
            "context": {
                "code": "Laboruntersuchung",
                "display": "Laboruntersuchung",
                "system": "fdpg.mii.cds",
                "version": "1.0.0"
            },
            "termCode": {
                "code": loinc,
                "display": lab["code_long_name"].strip() if lab["code_long_name"] else lab["swl_description"].strip(),
                "system": "http://loinc.org",
                "version": str(lab["version"]).strip()
            },
        }

        new_swl_node = {
            "context": {
                "code": "Laboruntersuchung",
                "display": "Laboruntersuchung",
                "system": "fdpg.mii.cds",
                "version": "1.0.0"
            },
            "termCode": {
                "code": swl_code,
                "display": lab["swl_description"].strip(),
                "system": "https://fhir.diz.uni-marburg.de/CodeSystem/swisslab-code",
                "version": ""
            },
        }

        if not belong_to or belong_to == "emptyvalue":
            if (loinc):
                queue[0]["children"].append(new_loinc_node)
            if (swl_code):
                queue[0]["children"].append(new_swl_node)
            continue
        
        # Breadth-First Search (BFS) with while and pop
        while queue:
            current_node = queue.pop(0)
            if current_node["termCode"]["code"] == belong_to:
                # Create a new node
                if ((loinc and loinc != "emptyvalue") or (swl_code and swl_code != "emptyvalue")):
                    if not any(child["termCode"]["code"] == loinc for child in current_node.get("children", [])):
                        current_node.setdefault("children", []).append(new_loinc_node)
                    if not any(child["termCode"]["code"] == swl_code for child in current_node.get("children", [])):
                        current_node.setdefault("children", []).append(new_swl_node)
                    found_parent = True
                break

            # add elements to the end of queue
            queue.extend(current_node.get("children", []))

        if not found_parent:
            current_node = queue.pop(0)
            if (loinc):
                current_node.setdefault("children", []).append(new_loinc_node)
            if (swl_code):
                current_node.setdefault("children", []).append(new_swl_node)

    with open("mapping_tree_new_lab.json", "w", encoding="utf-8") as f:
        json.dump(mapping_tree, f, ensure_ascii=False, indent=2)