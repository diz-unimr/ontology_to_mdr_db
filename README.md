# Ontology To MDR DB App
[![ESLint](https://github.com/diz-unimr/machbarkeit/actions/workflows/lint-eslint.yml/badge.svg)](https://github.com/diz-unimr/machbarkeit/actions/workflows/lint-eslint.yml)
[![Lint app info](https://github.com/diz-unimr/machbarkeit/actions/workflows/lint-info-xml.yml/badge.svg)](https://github.com/diz-unimr/machbarkeit/actions/workflows/lint-info-xml.yml)
[![PHP Coding Standards Fixer](https://github.com/diz-unimr/machbarkeit/actions/workflows/lint-php-cs.yml/badge.svg)](https://github.com/diz-unimr/machbarkeit/actions/workflows/lint-php-cs.yml)
[![Stylelint](https://github.com/diz-unimr/machbarkeit/actions/workflows/lint-stylelint.yml/badge.svg)](https://github.com/diz-unimr/machbarkeit/actions/workflows/lint-stylelint.yml)
[![PHPUnit](https://github.com/diz-unimr/machbarkeit/actions/workflows/phpunit-pgsql.yml/badge.svg)](https://github.com/diz-unimr/machbarkeit/actions/workflows/phpunit-pgsql.yml)
[![Package build](https://github.com/diz-unimr/machbarkeit/actions/workflows/appbuild.yml/badge.svg)](https://github.com/diz-unimr/machbarkeit/actions/workflows/appbuild.yml)
[![REUSE Compliance Check](https://github.com/diz-unimr/machbarkeit/actions/workflows/reuse.yml/badge.svg)](https://github.com/diz-unimr/machbarkeit/actions/workflows/reuse.yml)

To create Data and import them to MDR database, need the followed steps:
1. Read Ontology and Filter file (JSON File): Retrieve the ontology trees from FDPG [[ontology tree](https://github.com/diz-unimr/ontology_to_mdr_db/tree/main/ontology)]
2. Create "kds_beschreibung" table and save as csv file ("kds_beschreibung.csv"): This table will store KDS information. The data for each row will be extracted from the ontology trees.
3. Create "kds_concepts" table and save as csv file ("kds_concept.csv"): This table will store ontology concepts and the filtered data for each concept. The data for each row will be extracted from the ontology trees and filter file.
4. Import both files into MDR database
