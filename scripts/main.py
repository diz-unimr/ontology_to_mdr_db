from functions import *
from labor_ontology import *
from mapping import *

if __name__ == '__main__':

    #check_duplicate()
    ontology_trees_with_Lab = read_json_file(['ontology/ui_trees/Person.json', 'ontology/ui_trees/Diagnose.json', 'ontology/ui_trees/Prozedur.json', 'ontology/ui_trees/Laboruntersuchung.json'])
    ontology_trees = read_json_file(['ontology/ui_trees/Person.json', 'ontology/ui_trees/Diagnose.json', 'ontology/ui_trees/Prozedur.json'])
    create_modules_table(ontology_trees_with_Lab)
    create_concepts_table(ontology_trees)
    lab_categories = create_ontology_table()
    create_labor_mapping_tree(lab_categories)
    create_lab_codes_concepts_table()
    # insert_node_to_mapping_tree()