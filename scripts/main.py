from functions import *
from labor_ontology import create_lab_codes_concepts_table, create_ontology_table

if __name__ == '__main__':
    #connect_db()
    ontology_trees_with_Lab = read_json_file(['ontology/ui_trees/Person.json', 'ontology/ui_trees/Diagnose.json', 'ontology/ui_trees/Prozedur.json', 'ontology/ui_trees/Laboruntersuchung.json'])
    ontology_trees = read_json_file(['ontology/ui_trees/Person.json', 'ontology/ui_trees/Diagnose.json', 'ontology/ui_trees/Prozedur.json'])
    create_kds_beschreibung_table(ontology_trees_with_Lab)
    create_kds_concepts_table(ontology_trees)
    ontology_table = create_ontology_table()
    create_lab_codes_concepts_table(ontology_table)
    #close_db()