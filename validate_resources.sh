DIRECTORY=./dstu2
RESOURCE_DIRECTORY=$DIRECTORY/dr_with_referenced_labs_with_referenced_patient

java -jar validator_cli.jar $DIRECTORY/patient.json -version 1.0.2
java -jar validator_cli.jar $RESOURCE_DIRECTORY/diagnostic_report.json -version 1.0.2
java -jar validator_cli.jar $RESOURCE_DIRECTORY/lab_result_0.json -version 1.0.2
java -jar validator_cli.jar $RESOURCE_DIRECTORY/lab_result_1.json -version 1.0.2