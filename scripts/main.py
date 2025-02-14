from functions import *

if __name__ == '__main__':
    #connect_db()
    ontology_trees = read_json_file(['ontology/ui_trees/Person.json', 'ontology/ui_trees/Diagnose.json', 'ontology/ui_trees/Prozedur.json'])
    create_kds_beschreibung_table(ontology_trees)
    create_kds_concepts_table(ontology_trees)
    #close_db()
