import sys
from datetime import date, datetime
import json
import copy
import requests
from pathlib import Path
import argparse

from fhir.resources.DSTU2.patient import Patient
from fhir.resources.DSTU2.observation import Observation
from fhir.resources.DSTU2.codeableconcept import CodeableConcept
from fhir.resources.DSTU2.coding import Coding
from fhir.resources.DSTU2.extension import Extension
from fhir.resources.DSTU2.humanname import HumanName
from fhir.resources.DSTU2.identifier import Identifier
from fhir.resources.DSTU2.fhirreference import FHIRReference
from fhir.resources.DSTU2.fhirdate import FHIRDate
from fhir.resources.DSTU2.practitioner import Practitioner
from fhir.resources.DSTU2.organization import Organization
from fhir.resources.DSTU2.diagnosticreport import DiagnosticReport
from fhir.resources.DSTU2.period import Period

SUBJECT_INFO_EXTENSION_URL = "http://commonpass.org/fhir/StructureDefinition/subject-info"
SUBJECT_INFO_NAME_EXTENSION_URL = "http://commonpass.org/fhir/StructureDefinition/subject-name-info"

SUBJECT_IDENTIFIER_EXTENSION_URL = "http://commonpass.org/fhir/StructureDefinition/subject-identifier-info"

SUBJECT_INFO_PASSPORT_COUNTRY_EXTENSION_URL = "country"
SUBJECT_INFO_PASSPORT_NUMBER_EXTENSION_URL = "number"
SUBJECT_INFO_PASSPORT_EXPIRATION_EXTENSION_URL = "expiration"

LAB_RESULT_STATUS_FINAL = "final"
LAB_RESULT_CATEGORY_SYSTEM = "http://hl7.org/fhir/observation-category"
LAB_RESULT_CATEGORY_CODE = "laboratory"
LOINC_SYSTEM = "http://loinc.org"

DIAGNOSTIC_REPORT_STATUS_FINAL = "final"
DIAGNOSTIC_REPORT_CATEGORY_SYSTEM = "http://hl7.org/fhir/DiagnosticReport-category"
DIAGNOSTIC_REPORT_CATEGORY_CODE = "LAB"

OBSERVATION_INTERPRETATION_CODE_SYSTEM = "http://hl7.org/fhir/v2/0078"
OBSERVATION_INTERPRETATION_CODE_NORMAL = "N"

TEST_MANUFACTURER_MODEL_SYSTEM = "http://commonpass.org/fhir/StructureDefinition/test-manufacturer-model"
TEST_MANUFACTURER_MODEL_CODE = "TBD"

TEST_IDENTIFIER_EXTENSION_URL = "http://commonpass.org/fhir/StructureDefinition/test-identifier"
TEST_IDENTIFIER_EXTENSION_VALUE = "0123456789"

IDENTIFIER_CODE_SYSTEM = "http://hl7.org/fhir/v2/0203"
IDENTIFIER_PASSPORT_CODE = "PPN"
IDENTIFIER_USE_OFFICIAL = "official"

def create_passport_identifier(passport_country, passport_number, passport_expiration_date):

    identifier = Identifier()
    identifier.value = passport_number

    assigner = FHIRReference()
    assigner.display = passport_country
    identifier.assigner = assigner

    period = Period()
    expiration_date = FHIRDate()
    expiration_date.date = passport_expiration_date
    period.end = expiration_date
    identifier.period = period

    coding = Coding()
    coding.system = IDENTIFIER_CODE_SYSTEM
    coding.code = IDENTIFIER_PASSPORT_CODE
    coding.display = "Passport Number"
    codable_concept = CodeableConcept()
    codable_concept.coding = [coding]

    identifier.type = codable_concept

    return identifier

def get_passport_identifiers(patient):
    passport_identifiers = []
    for identifier in patient.identifier:
        if identifier.type != None and identifier.type.coding != None:
            for coding in identifier.type.coding:
                if coding.system == IDENTIFIER_CODE_SYSTEM and coding.code == IDENTIFIER_PASSPORT_CODE:
                    passport_identifiers.append(identifier)

    return passport_identifiers

# def get_passport_info_extension(patient):
#     for extension in patient.extension:
#         if extension.url == SUBJECT_INFO_PASSPORT_EXTENSION_URL:
#             return extension

#     return None

def create_subject_name_extension(human_name):
    extension = Extension()
    extension.url = SUBJECT_INFO_NAME_EXTENSION_URL
    extension.valueHumanName = human_name

    return extension

def create_subject_identifier_extension(identifier):
    extension = Extension()
    extension.url = SUBJECT_IDENTIFIER_EXTENSION_URL
    extension.valueIdentifier = identifier

    return extension


def create_subject_info_extension(patient):

    extension = Extension()
    extension.url = SUBJECT_INFO_EXTENSION_URL
    extension.extension = [
        create_subject_name_extension(patient.name[0])
    ]

    passport_identifiers = get_passport_identifiers(patient)
    for passport_identifier in passport_identifiers:
        extension.extension.append(
            create_subject_identifier_extension(passport_identifier)
        ) 

    return extension
    
def create_patient(given_name, family_name, passports):
    patient = Patient()
    name = HumanName()
    name.family = [family_name]
    name.given = [given_name]
    patient.name = [name]

    passport_identifiers = []
    for passport in passports:
        passport_identifier = create_passport_identifier(
            passport["passport_country"], 
            passport["passport_number"], 
            date.fromisoformat(passport['passport_expiration'])
        )
        passport_identifiers.append(passport_identifier)

    patient.identifier = passport_identifiers

    return patient

def get_human_readable_name(name):
    return " ".join(name.given + name.family)

def create_codable_concept_with_single_coding(system, code, display, coding_extension):
    coding = Coding()
    coding.system = system
    coding.code = code
    coding.display = display
    if coding_extension != None:
        coding.extension = [coding_extension]
    codable_concept = CodeableConcept()
    codable_concept.coding = [coding]
    return codable_concept

# a status
# a category code of ‘laboratory’
# a LOINC code which tells you what is being measured
# Patient PII (including passport information)
# a result value and, if the result value is a numeric quantity, a standard UCUM unit
# an interpretation
# effective time
# issued time
# Test manufacturer and test model (and optionally, a unique identifier for the test instance)
# Testing facility and test administrator
def create_lab_result_with_contained_patient(patient, test_facility, test_administrator, code_code, code_display, effective_date, issued_date, interpretation, valueString=None, valueQuantity=None, valueCodeableConcept=None):
    
    contained = []
    
    ##status
    lab_result = Observation()
    lab_result.status = LAB_RESULT_STATUS_FINAL

    ##category
    lab_result.category = create_codable_concept_with_single_coding(
        LAB_RESULT_CATEGORY_SYSTEM, 
        LAB_RESULT_CATEGORY_CODE,
        None,
        None
    )

    ##code
    lab_result.code = create_codable_concept_with_single_coding(
        LOINC_SYSTEM,
        code_code,
        code_display,
        None
    )

    ##patient

    patient_reference = FHIRReference()
    patient_reference.reference = f'#{patient.id}'

    contained.append(patient)
    lab_result.subject = patient_reference

    ##value
    if valueString:
        lab_result.valueString = valueString
    elif valueQuantity:
        lab_result.valueQuantity = valueQuantity
    elif valueCodeableConcept:
        lab_result.valueCodeableConcept = valueCodeableConcept

    ##interpretation
    lab_result.interpretation = create_codable_concept_with_single_coding(
        OBSERVATION_INTERPRETATION_CODE_SYSTEM, 
        interpretation,
        None,
        None
    )

    ## effective time
    effective = FHIRDate()
    effective.date = effective_date
    lab_result.effectiveDateTime = effective

    ## issued time
    issued = FHIRDate()
    issued.date = issued_date
    lab_result.issued = issued

    ##test manufacturer and model (and unique identifier)
    test_id_extension = Extension()
    test_id_extension.url = TEST_IDENTIFIER_EXTENSION_URL
    test_id_extension.valueString = TEST_IDENTIFIER_EXTENSION_VALUE

    lab_result.method = create_codable_concept_with_single_coding(
        TEST_MANUFACTURER_MODEL_SYSTEM,
        TEST_MANUFACTURER_MODEL_CODE,
        None,
        test_id_extension
    )

    ##test performer(s)
    test_facility_reference = FHIRReference()
    test_facility_reference.reference = f'#{test_facility.id}'
    test_facility_reference.display = test_facility.name
    test_administrator_reference = FHIRReference()
    test_administrator_reference.reference = f'#{test_administrator.id}'
    test_administrator_reference.display = get_human_readable_name(test_facility.name)

    contained.extend([test_facility, test_administrator])
    lab_result.performer = [test_facility_reference, test_administrator_reference]

    lab_result.contained = contained

    return lab_result

# a status
# a category code of ‘laboratory’
# a LOINC code which tells you what is being measured
# Patient PII (including passport information)
# a result value and, if the result value is a numeric quantity, a standard UCUM unit
# an interpretation
# effective time
# issued time
# Test manufacturer and test model (and optionally, a unique identifier for the test instance)
# Testing facility and test administrator
def create_lab_result_with_referenced_patient(patient, test_facility, test_administrator, code_code, code_display, effective_date, issued_date, interpretation, valueString=None, valueQuantity=None, valueCodeableConcept=None):
    
    contained = []
    
    ##status
    lab_result = Observation()
    lab_result.status = LAB_RESULT_STATUS_FINAL

    ##category
    lab_result.category = create_codable_concept_with_single_coding(
        LAB_RESULT_CATEGORY_SYSTEM, 
        LAB_RESULT_CATEGORY_CODE,
        None,
        None
    )

    ##code
    lab_result.code = create_codable_concept_with_single_coding(
        LOINC_SYSTEM,
        code_code,
        code_display,
        None
    )

    ##patient
    ##reference the patient, but add the patient info extension

    patient_reference = FHIRReference()
    patient_reference.reference = f'Patient/{patient.id}'

    patient_reference.display = get_human_readable_name(patient.name[0])
    patient_info_extension = create_subject_info_extension(patient)
    patient_reference.extension = [
        patient_info_extension
    ]
    lab_result.subject = patient_reference

    ##value
    if valueString:
        lab_result.valueString = valueString
    elif valueQuantity:
        lab_result.valueQuantity = valueQuantity
    elif valueCodeableConcept:
        lab_result.valueCodeableConcept = valueCodeableConcept

    ##interpretation
    lab_result.interpretation = create_codable_concept_with_single_coding(
        OBSERVATION_INTERPRETATION_CODE_SYSTEM, 
        interpretation,
        None,
        None
    )

    ## effective time
    effective = FHIRDate()
    effective.date = effective_date
    lab_result.effectiveDateTime = effective

    ## issued time
    issued = FHIRDate()
    issued.date = issued_date
    lab_result.issued = issued

    ##test manufacturer and model (and unique identifier)
    test_id_extension = Extension()
    test_id_extension.url = TEST_IDENTIFIER_EXTENSION_URL
    test_id_extension.valueString = TEST_IDENTIFIER_EXTENSION_VALUE

    lab_result.method = create_codable_concept_with_single_coding(
        TEST_MANUFACTURER_MODEL_SYSTEM,
        TEST_MANUFACTURER_MODEL_CODE,
        None,
        test_id_extension
    )

    ##test performer(s)
    test_facility_reference = FHIRReference()
    test_facility_reference.reference = f'#{test_facility.id}'
    test_facility_reference.display = test_facility.name
    test_administrator_reference = FHIRReference()
    test_administrator_reference.reference = f'#{test_administrator.id}'
    test_administrator_reference.display = get_human_readable_name(test_administrator.name)

    contained.extend([test_facility, test_administrator])
    lab_result.performer = [test_facility_reference, test_administrator_reference]

    lab_result.contained = contained

    return lab_result

def create_lab_organization(organization_id, name):
    organization = Organization()
    organization.id = organization_id
    organization.name = name

    return organization

def create_lab_tech(practitioner_id, given_name, family_name):
    practitioner = Practitioner()
    practitioner.id = practitioner_id
    name = HumanName()
    name.family = [family_name]
    name.given = [given_name]
    practitioner.name = name

    return practitioner


# a status
# a category code of ‘LAB’
# a code (preferably a LOINC code) which tells you what is being measured
# a patient
# a time indicating when the measurement was taken
# a time indicating when the measurement was reported
# who issues the report
# references to the lab result Observation resources (either contained or standalone resources)

def create_diagnostic_report_with_referenced_observations(patient, test_facility, code_code, code_display, effective_date, issued_date, results):

    contained = []

    diagnostic_report = DiagnosticReport()

    diagnostic_report.status = DIAGNOSTIC_REPORT_STATUS_FINAL

    ##category
    diagnostic_report.category = create_codable_concept_with_single_coding(
        DIAGNOSTIC_REPORT_CATEGORY_SYSTEM, 
        DIAGNOSTIC_REPORT_CATEGORY_CODE,
        None,
        None
    )

    ##code
    diagnostic_report.code = create_codable_concept_with_single_coding(
        LOINC_SYSTEM,
        code_code,
        code_display,
        None
    )

    ##patient
    patient_reference = FHIRReference()
    patient_reference.reference = f'Patient/{patient.id}'
    patient_reference.display = get_human_readable_name(patient.name[0])
    patient_info_extension = create_subject_info_extension(patient)
    patient_reference.extension = [
        patient_info_extension
    ]
    diagnostic_report.subject = patient_reference

    # contained.append(patient)
    diagnostic_report.subject = patient_reference

    ## effective time
    effective = FHIRDate()
    effective.date = effective_date
    diagnostic_report.effectiveDateTime = effective

    ## issued time
    issued = FHIRDate()
    issued.date = issued_date
    diagnostic_report.issued = issued

    ##test performer(s)
    test_facility_reference = FHIRReference()
    # test_facility_reference.reference = f'Organization/{test_facility.id}'

    test_facility_reference.reference = f'#{test_facility.id}'
    test_facility_reference.display = test_facility.name
    contained.append(test_facility)
    diagnostic_report.performer = test_facility_reference

    #results
    diagnostic_report.result = []
    for index, result in enumerate(results):
        # result_copy = copy.copy(result)
        # result_copy.id = str(index + 1)
        # contained.append(result_copy)

        result_reference = FHIRReference()
        result_reference.reference = f'Observation/{result.id}'

        diagnostic_report.result.append(result_reference)

    diagnostic_report.contained = contained
    return diagnostic_report

def create_diagnostic_report_with_contained_observations(patient, test_facility, code_code, code_display, effective_date, issued_date, results):

    contained = []

    diagnostic_report = DiagnosticReport()

    diagnostic_report.status = DIAGNOSTIC_REPORT_STATUS_FINAL

    ##category
    diagnostic_report.category = create_codable_concept_with_single_coding(
        DIAGNOSTIC_REPORT_CATEGORY_SYSTEM, 
        DIAGNOSTIC_REPORT_CATEGORY_CODE,
        None,
        None
    )

    ##code
    diagnostic_report.code = create_codable_concept_with_single_coding(
        LOINC_SYSTEM,
        code_code,
        code_display,
        None
    )

    ##patient
    patient_reference = FHIRReference()
    patient_reference.reference = f'Patient/{patient.id}'
    patient_reference.display = get_human_readable_name(patient.name[0])
    patient_info_extension = create_subject_info_extension(patient)
    patient_reference.extension = [
        patient_info_extension
    ]
    diagnostic_report.subject = patient_reference

    ## effective time
    effective = FHIRDate()
    effective.date = effective_date
    diagnostic_report.effectiveDateTime = effective

    ## issued time
    issued = FHIRDate()
    issued.date = issued_date
    diagnostic_report.issued = issued

    ##test performer(s)
    test_facility_reference = FHIRReference()
    # test_facility_reference.reference = f'Organization/{test_facility.id}'
    test_facility_reference.reference = f'#{test_facility.id}'
    test_facility_reference.display = test_facility.name
    contained.append(test_facility)
    diagnostic_report.performer = test_facility_reference

    #results
    diagnostic_report.result = []
    for index, result in enumerate(results):
        result_copy = copy.copy(result)
        result_copy.id = str(index + 1)
        contained.append(result_copy)

        result_reference = FHIRReference()
        result_reference.reference = f'#{result_copy.id}'

        diagnostic_report.result.append(result_reference)

    diagnostic_report.contained = contained
    return diagnostic_report

def upload_patient(patient, base_url):
    request_url = f'{base_url}/Patient'

    r = requests.post(
        request_url,
        json=patient.as_json()
    )

    r.raise_for_status()

    return Patient(r.json())

def get_patient(patient_id, base_url):

    request_url = f'{base_url}/Patient/{patient_id}'

    r = requests.get(
        request_url
    )

    r.raise_for_status()

    return Patient(r.json())

def upload_diagnostic_report(diagnostic_report, base_url):
    request_url = f'{base_url}/DiagnosticReport'

    r = requests.post(
        request_url,
        json=diagnostic_report.as_json()
    )

    r.raise_for_status()

    return DiagnosticReport(r.json())

def upload_observation(observation, base_url):
    request_url = f'{base_url}/Observation'

    r = requests.post(
        request_url,
        json=observation.as_json()
    )

    r.raise_for_status()

    return Observation(r.json())


# patient = create_patient(
#     "Test", 
#     "Patient",
#     "12345678-90",
#     "United States of America",
#     date.fromisoformat('2024-12-04')
# )

# uploaded_patient = upload_patient(patient)
# # uploaded_patient = get_patient("565010")
# print(uploaded_patient.as_json())


# organization = create_lab_organization(
#     "8932748723984",
#     "Test Facility A"
# )

# lab_tech = create_lab_tech(
#     "23980293840932",
#     "Lab",
#     "Tech"
# )

# lab_result_a = create_lab_result_with_referenced_patient(
#     uploaded_patient,
#     organization,
#     lab_tech,
#     "94564-2",
#     "SARS-CoV-2 Antibody, IgM",
#     datetime.now(),
#     datetime.now(),
#     valueString="Negative"
# )

# uploaded_lab_result_a = upload_observation(lab_result_a)
# print(uploaded_lab_result_a.as_json())

# lab_result_b = create_lab_result_with_referenced_patient(
#     uploaded_patient,
#     organization,
#     lab_tech,
#     "94500-6",
#     "SARS-COV-2, NAA",
#     datetime.now(),
#     datetime.now(),
#     valueString="Indeterminate"
# )

# uploaded_lab_result_b = upload_observation(lab_result_b)
# print(uploaded_lab_result_b.as_json())

# # lab_result_a_json_string = json.dumps(lab_result_a.as_json())
# # print(lab_result_a_json_string)

# # lab_result_b_json_string = json.dumps(lab_result_b.as_json())
# # print(lab_result_b_json_string)

# # patient = create_patient("James", "Kizer")
# # print(patient.as_json())

# diagnostic_report = create_diagnostic_report(
#     uploaded_patient,
#     organization,
#     "94500-6",
#     "SARS-COV-2, NAA",
#     datetime.now(),
#     datetime.now(),
#     [uploaded_lab_result_a, uploaded_lab_result_b]
# )

# # diagnostic_report_json_string = json.dumps(diagnostic_report.as_json())
# # print(diagnostic_report_json_string)

# uploaded_diagnostic_report = upload_diagnostic_report(
#     diagnostic_report
# )

# diagnostic_report_json_string = json.dumps(uploaded_diagnostic_report.as_json())
# print(diagnostic_report_json_string)

def write_resource_to_file(resource, filename):
    with open(filename, "w") as outfile: 
        json.dump(resource.as_json(), outfile, indent = 4) 


##Cases

## 1 - Diagnostic report with contained lab results
##lab results MUST reference patient and include patient info in extension
def create_dr_with_contained_labs(uploaded_patient, organization, lab_tech, diagnostic_report_info, lab_result_infos, base_url, output_directory_name):

    output_dir = f'./{output_directory_name}/dr_with_contained_labs' 
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    lab_results = []
    for lab_result_info in lab_result_infos:
        lab_result = create_lab_result_with_referenced_patient(
            uploaded_patient,
            organization,
            lab_tech,
            lab_result_info['code_code'],
            lab_result_info['code_display'],
            datetime.fromisoformat(lab_result_info['effective']).astimezone(),
            datetime.fromisoformat(lab_result_info['issued']).astimezone(),
            lab_result_info['interpretation'],
            valueString=lab_result_info['valueString']
        )
        lab_results.append(lab_result)

    diagnostic_report = create_diagnostic_report_with_contained_observations(
        uploaded_patient,
        organization,
        diagnostic_report_info['code_code'],
        diagnostic_report_info['code_display'],
        datetime.fromisoformat(diagnostic_report_info['effective']).astimezone(),
        datetime.fromisoformat(diagnostic_report_info['issued']).astimezone(),
        lab_results
    )

    write_resource_to_file(
        diagnostic_report,
        f'{output_dir}/diagnostic_report_pre_upload.json'
    )

    uploaded_diagnostic_report = upload_diagnostic_report(
        diagnostic_report,
        base_url
    )

    write_resource_to_file(
        uploaded_diagnostic_report,
        f'{output_dir}/diagnostic_report.json'
    )


## 2 - Diagnostic report with referenced labs, lab results contain patient
def create_dr_with_referenced_labs_with_contained_patient(uploaded_patient, organization, lab_tech, diagnostic_report_info, lab_result_infos, base_url, output_directory_name):

    output_dir = f'./{output_directory_name}/dr_with_referenced_labs_with_contained_patient' 
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    lab_results = []
    for (i, lab_result_info) in enumerate(lab_result_infos):
        lab_result = create_lab_result_with_contained_patient(
            uploaded_patient,
            organization,
            lab_tech,
            lab_result_info['code_code'],
            lab_result_info['code_display'],
            datetime.fromisoformat(lab_result_info['effective']).astimezone(),
            datetime.fromisoformat(lab_result_info['issued']).astimezone(),
            lab_result_info['interpretation'],
            valueString=lab_result_info['valueString']
        )

        write_resource_to_file(
            lab_result,
            f'{output_dir}/lab_result_{i}_pre_upload.json'
        )

        uploaded_lab_result = upload_observation(lab_result, base_url)
        write_resource_to_file(
            uploaded_lab_result,
            f'{output_dir}/lab_result_{i}.json'
        )

        lab_results.append(uploaded_lab_result)

    diagnostic_report = create_diagnostic_report_with_referenced_observations(
        uploaded_patient,
        organization,
        diagnostic_report_info['code_code'],
        diagnostic_report_info['code_display'],
        datetime.fromisoformat(diagnostic_report_info['effective']).astimezone(),
        datetime.fromisoformat(diagnostic_report_info['issued']).astimezone(),
        lab_results
    )

    write_resource_to_file(
        diagnostic_report,
        f'{output_dir}/diagnostic_report_pre_upload.json'
    )

    uploaded_diagnostic_report = upload_diagnostic_report(
        diagnostic_report,
        base_url
    )

    write_resource_to_file(
        uploaded_diagnostic_report,
        f'{output_dir}/diagnostic_report.json'
    )


## 3 - Diagnostic report with referenced labs, lab results DO NOT contain patient, and must include patient info extension
def create_dr_with_referenced_labs_with_referenced_patient(uploaded_patient, organization, lab_tech, diagnostic_report_info, lab_result_infos, base_url, output_directory_name):

    output_dir = f'./{output_directory_name}/dr_with_referenced_labs_with_referenced_patient' 
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    lab_results = []
    for (i, lab_result_info) in enumerate(lab_result_infos):
        lab_result = create_lab_result_with_referenced_patient(
            uploaded_patient,
            organization,
            lab_tech,
            lab_result_info['code_code'],
            lab_result_info['code_display'],
            datetime.fromisoformat(lab_result_info['effective']).astimezone(),
            datetime.fromisoformat(lab_result_info['issued']).astimezone(),
            lab_result_info['interpretation'],
            valueString=lab_result_info['valueString']
        )

        write_resource_to_file(
            lab_result,
            f'{output_dir}/lab_result_{i}_pre_upload.json'
        )

        uploaded_lab_result = upload_observation(lab_result, base_url)
        write_resource_to_file(
            uploaded_lab_result,
            f'{output_dir}/lab_result_{i}.json'
        )

        lab_results.append(uploaded_lab_result)

    diagnostic_report = create_diagnostic_report_with_referenced_observations(
        uploaded_patient,
        organization,
        diagnostic_report_info['code_code'],
        diagnostic_report_info['code_display'],
        datetime.fromisoformat(diagnostic_report_info['effective']).astimezone(),
        datetime.fromisoformat(diagnostic_report_info['issued']).astimezone(),
        lab_results
    )

    write_resource_to_file(
        diagnostic_report,
        f'{output_dir}/diagnostic_report_pre_upload.json'
    )

    uploaded_diagnostic_report = upload_diagnostic_report(
        diagnostic_report,
        base_url
    )

    write_resource_to_file(
        uploaded_diagnostic_report,
        f'{output_dir}/diagnostic_report.json'
    )

def main():

    parser = argparse.ArgumentParser(description='Generates sample Patient, DiagnosticReport, and Observation resources')
    parser.add_argument('config_file', help='Config file')

    args = parser.parse_args()
    with open(args.config_file, 'r', newline='') as config_file:
        config_json_string = config_file.read()
        config = json.loads(config_json_string)

    base_url = config['unprotected_base_url']
    output_directory_name = config['output_directory_name']
    patient_info = config['patient']
    organization_info = config['organization']
    lab_tech_info = config['lab_tech']
    diagnostic_report_info = config['diagnostic_report']
    lab_result_infos = config['lab_results']
    Path(f'./{output_directory_name}').mkdir(parents=True, exist_ok=True)

    args = parser.parse_args()

    patient = create_patient(
        patient_info['given_name'], 
        patient_info['family_name'],
        patient_info['passports']
    )

    write_resource_to_file(
        patient,
        f'./{output_directory_name}/patient_pre_upload.json'
    )

    uploaded_patient = upload_patient(patient, base_url)

    write_resource_to_file(
        uploaded_patient,
        f'./{output_directory_name}/patient.json'
    )

    organization = create_lab_organization(
        organization_info["id"],
        organization_info["name"]
    )

    lab_tech = create_lab_tech(
        lab_tech_info["id"],
        lab_tech_info["given_name"],
        lab_tech_info["family_name"]
    )

    # create_dr_with_contained_labs(uploaded_patient, organization, lab_tech, diagnostic_report_info, lab_result_infos, base_url, output_directory_name)
    # create_dr_with_referenced_labs_with_contained_patient(uploaded_patient, organization, lab_tech, diagnostic_report_info, lab_result_infos, base_url, output_directory_name)
    create_dr_with_referenced_labs_with_referenced_patient(uploaded_patient, organization, lab_tech, diagnostic_report_info, lab_result_infos, base_url, output_directory_name)

    print(f'Created resources for patient ID: {uploaded_patient.id}')

if __name__ == "__main__":
    main()