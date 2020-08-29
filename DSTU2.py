import sys
from datetime import date, datetime
import json
import copy
import requests

from fhir.resources.DSTU2.patient import Patient
from fhir.resources.DSTU2.observation import Observation
from fhir.resources.DSTU2.codeableconcept import CodeableConcept
from fhir.resources.DSTU2.coding import Coding
from fhir.resources.DSTU2.extension import Extension
from fhir.resources.DSTU2.humanname import HumanName
from fhir.resources.DSTU2.fhirreference import FHIRReference
from fhir.resources.DSTU2.fhirdate import FHIRDate
from fhir.resources.DSTU2.practitioner import Practitioner
from fhir.resources.DSTU2.organization import Organization
from fhir.resources.DSTU2.diagnosticreport import DiagnosticReport

SUBJECT_INFO_EXTENSION_URL = "http://commonpass.org/fhir/StructureDefinition/subject-info"
SUBJECT_INFO_NAME_EXTENSION_URL = "http://commonpass.org/fhir/StructureDefinition/subject-name-info"

SUBJECT_INFO_PASSPORT_EXTENSION_URL = "http://commonpass.org/fhir/StructureDefinition/subject-passport-info"
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
TEST_MANUFACTURER_MODEL_CODE = "MANUFACTURER_AND_MODEL"

TEST_IDENTIFIER_EXTENSION_URL = "http://commonpass.org/fhir/StructureDefinition/test-identifier"
TEST_IDENTIFIER_EXTENSION_VALUE = "0123456789"

base_url = "https://r2.smarthealthit.org"

def create_passport_info_extension(passport_country, passport_number, passport_expiration_date):

    passport_info_country_extension = Extension()
    passport_info_country_extension.url = SUBJECT_INFO_PASSPORT_COUNTRY_EXTENSION_URL
    passport_info_country_extension.valueString = passport_country

    passport_info_number_extension = Extension()
    passport_info_number_extension.url = SUBJECT_INFO_PASSPORT_NUMBER_EXTENSION_URL
    passport_info_number_extension.valueString = passport_number

    passport_info_expiration_extension = Extension()
    passport_info_expiration_extension.url = SUBJECT_INFO_PASSPORT_EXPIRATION_EXTENSION_URL
    expiration_date = FHIRDate()
    expiration_date.date = passport_expiration_date
    passport_info_expiration_extension.valueDate = expiration_date

    passport_extension = Extension()
    passport_extension.url = SUBJECT_INFO_PASSPORT_EXTENSION_URL
    passport_extension.extension = [
        passport_info_country_extension,
        passport_info_number_extension,
        passport_info_expiration_extension
    ]

    return passport_extension

def get_passport_info_extension(patient):
    for extension in patient.extension:
        if extension.url == SUBJECT_INFO_PASSPORT_EXTENSION_URL:
            return extension

    return None

def create_subject_name_extension(human_name):
    extension = Extension()
    extension.url = SUBJECT_INFO_NAME_EXTENSION_URL
    extension.valueHumanName = human_name

    return extension


def create_subject_info_extension(patient):

    extension = Extension()
    extension.url = SUBJECT_INFO_EXTENSION_URL
    extension.extension = [
        create_subject_name_extension(patient.name[0]),
        get_passport_info_extension(patient)
    ]

    return extension
    
def create_patient(given_name, family_name, passport_number, passport_country, passport_expiration_date):
    patient = Patient()
    name = HumanName()
    name.family = [family_name]
    name.given = [given_name]
    patient.name = [name]

    passport_extension = create_passport_info_extension(passport_country, passport_number, passport_expiration_date)

    patient.extension = [passport_extension]

    return patient

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
def create_lab_result_with_contained_patient(patient, test_facility, test_administrator, code_code, code_display, effective_date, issued_date, valueString=None, valueQuantity=None, valueCodeableConcept=None):
    
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
        OBSERVATION_INTERPRETATION_CODE_NORMAL,
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
    test_administrator_reference = FHIRReference()
    test_administrator_reference.reference = f'#{test_administrator.id}'

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
def create_lab_result_with_referenced_patient(patient, test_facility, test_administrator, code_code, code_display, effective_date, issued_date, valueString=None, valueQuantity=None, valueCodeableConcept=None):
    
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
    lab_result.subject = patient_reference

    patient_info_extension = create_subject_info_extension(patient)
    lab_result.extension = [
        patient_info_extension
    ]

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
        OBSERVATION_INTERPRETATION_CODE_NORMAL,
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
    test_administrator_reference = FHIRReference()
    test_administrator_reference.reference = f'#{test_administrator.id}'

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

def upload_patient(patient):
    request_url = f'{base_url}/Patient'

    r = requests.post(
        request_url,
        json=patient.as_json()
    )

    r.raise_for_status()

    return Patient(r.json())

def get_patient(patient_id):

    request_url = f'{base_url}/Patient/{patient_id}'

    r = requests.get(
        request_url
    )

    r.raise_for_status()

    return Patient(r.json())

def upload_diagnostic_report(diagnostic_report):
    request_url = f'{base_url}/DiagnosticReport'

    r = requests.post(
        request_url,
        json=diagnostic_report.as_json()
    )

    r.raise_for_status()

    return DiagnosticReport(r.json())

def upload_observation(observation):
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
def create_dr_with_contained_labs():
    patient = create_patient(
        "Test", 
        "Patient",
        "12345678-90",
        "United States of America",
        date.fromisoformat('2024-12-04')
    )

    uploaded_patient = upload_patient(patient)

    write_resource_to_file(
        uploaded_patient,
        "dr_with_contained_labs/patient.json"
    )

    organization = create_lab_organization(
        "8932748723984",
        "Test Facility A"
    )

    lab_tech = create_lab_tech(
        "23980293840932",
        "Lab",
        "Tech"
    )

    lab_result_a = create_lab_result_with_referenced_patient(
        uploaded_patient,
        organization,
        lab_tech,
        "94564-2",
        "SARS-CoV-2 Antibody, IgM",
        datetime.now(),
        datetime.now(),
        valueString="Negative"
    )

    lab_result_b = create_lab_result_with_referenced_patient(
        uploaded_patient,
        organization,
        lab_tech,
        "94500-6",
        "SARS-COV-2, NAA",
        datetime.now(),
        datetime.now(),
        valueString="Indeterminate"
    )

    diagnostic_report = create_diagnostic_report_with_contained_observations(
        uploaded_patient,
        organization,
        "94500-6",
        "SARS-COV-2, NAA",
        datetime.now(),
        datetime.now(),
        [lab_result_a, lab_result_b]
    )

    uploaded_diagnostic_report = upload_diagnostic_report(
        diagnostic_report
    )

    write_resource_to_file(
        uploaded_diagnostic_report,
        "dr_with_contained_labs/diagnostic_report.json"
    )










## 2 - Diagnostic report with referenced labs, lab results contain patient
def create_dr_with_referenced_labs_with_contained_patient():

    patient = create_patient(
        "Test", 
        "Patient",
        "12345678-90",
        "United States of America",
        date.fromisoformat('2024-12-04')
    )

    uploaded_patient = upload_patient(patient)

    write_resource_to_file(
        uploaded_patient,
        "dr_with_referenced_labs_with_contained_patient/patient.json"
    )

    organization = create_lab_organization(
        "8932748723984",
        "Test Facility A"
    )

    lab_tech = create_lab_tech(
        "23980293840932",
        "Lab",
        "Tech"
    )

    lab_result_a = create_lab_result_with_contained_patient(
        uploaded_patient,
        organization,
        lab_tech,
        "94564-2",
        "SARS-CoV-2 Antibody, IgM",
        datetime.now(),
        datetime.now(),
        valueString="Negative"
    )

    uploaded_lab_result_a = upload_observation(lab_result_a)
    write_resource_to_file(
        uploaded_lab_result_a,
        "dr_with_referenced_labs_with_contained_patient/lab_result_a.json"
    )

    lab_result_b = create_lab_result_with_contained_patient(
        uploaded_patient,
        organization,
        lab_tech,
        "94500-6",
        "SARS-COV-2, NAA",
        datetime.now(),
        datetime.now(),
        valueString="Indeterminate"
    )

    uploaded_lab_result_b = upload_observation(lab_result_b)
    write_resource_to_file(
        uploaded_lab_result_b,
        "dr_with_referenced_labs_with_contained_patient/lab_result_b.json"
    )

    diagnostic_report = create_diagnostic_report_with_referenced_observations(
        uploaded_patient,
        organization,
        "94500-6",
        "SARS-COV-2, NAA",
        datetime.now(),
        datetime.now(),
        [uploaded_lab_result_a, uploaded_lab_result_b]
    )

    uploaded_diagnostic_report = upload_diagnostic_report(
        diagnostic_report
    )

    write_resource_to_file(
        uploaded_diagnostic_report,
        "dr_with_referenced_labs_with_contained_patient/diagnostic_report.json"
    )


## 3 - Diagnostic report with referenced labs, lab results DO NOT contain patient, and must include patient info extension
def create_dr_with_referenced_labs_with_referenced_patient():

    patient = create_patient(
        "Test", 
        "Patient",
        "12345678-90",
        "United States of America",
        date.fromisoformat('2024-12-04')
    )

    uploaded_patient = upload_patient(patient)

    write_resource_to_file(
        uploaded_patient,
        "dr_with_referenced_labs_with_referenced_patient/patient.json"
    )

    organization = create_lab_organization(
        "8932748723984",
        "Test Facility A"
    )

    lab_tech = create_lab_tech(
        "23980293840932",
        "Lab",
        "Tech"
    )

    lab_result_a = create_lab_result_with_referenced_patient(
        uploaded_patient,
        organization,
        lab_tech,
        "94564-2",
        "SARS-CoV-2 Antibody, IgM",
        datetime.now(),
        datetime.now(),
        valueString="Negative"
    )

    uploaded_lab_result_a = upload_observation(lab_result_a)
    write_resource_to_file(
        uploaded_lab_result_a,
        "dr_with_referenced_labs_with_referenced_patient/lab_result_a.json"
    )

    lab_result_b = create_lab_result_with_referenced_patient(
        uploaded_patient,
        organization,
        lab_tech,
        "94500-6",
        "SARS-COV-2, NAA",
        datetime.now(),
        datetime.now(),
        valueString="Indeterminate"
    )

    uploaded_lab_result_b = upload_observation(lab_result_b)
    write_resource_to_file(
        uploaded_lab_result_b,
        "dr_with_referenced_labs_with_referenced_patient/lab_result_b.json"
    )

    diagnostic_report = create_diagnostic_report_with_referenced_observations(
        uploaded_patient,
        organization,
        "94500-6",
        "SARS-COV-2, NAA",
        datetime.now(),
        datetime.now(),
        [uploaded_lab_result_a, uploaded_lab_result_b]
    )

    uploaded_diagnostic_report = upload_diagnostic_report(
        diagnostic_report
    )

    write_resource_to_file(
        uploaded_diagnostic_report,
        "dr_with_referenced_labs_with_referenced_patient/diagnostic_report.json"
    )



# create_dr_with_contained_labs()
# create_dr_with_referenced_labs_with_contained_patient()
create_dr_with_referenced_labs_with_referenced_patient()