from typing import Optional, List

from apps.document.field_types import FIELD_TYPES_REGISTRY
from apps.document.field_types import FieldType
from apps.document.fields_detection.fields_detection_abstractions import FieldDetectionStrategy, DetectedFieldValue, \
    ProcessLogger
from apps.document.models import ClassifierModel, TextUnit
from apps.document.models import DocumentType, DocumentField, Document
from apps.document.python_coded_fields import PYTHON_CODED_FIELDS_REGISTRY, PythonCodedField


class PythonCodedFieldDetectionStrategy(FieldDetectionStrategy):
    code = DocumentField.VD_PYTHON_CODED_FIELD

    @classmethod
    def uses_cached_document_field_values(cls, field: DocumentField):
        python_coded_field = PYTHON_CODED_FIELDS_REGISTRY.get(field.python_coded_field)  # type: PythonCodedField
        if not python_coded_field:
            raise RuntimeError('Unknown python-coded field: {0}'.format(field.python_coded_field))

        return python_coded_field.uses_cached_document_field_values

    @classmethod
    def train_document_field_detector_model(cls,
                                            log: ProcessLogger,
                                            document_type: DocumentType,
                                            field: DocumentField,
                                            train_data_project_ids: Optional[List],
                                            use_only_confirmed_field_values: bool = False) -> Optional[ClassifierModel]:
        python_coded_field = PYTHON_CODED_FIELDS_REGISTRY.get(field.python_coded_field)  # type: PythonCodedField
        if not python_coded_field:
            raise RuntimeError('Unknown python-coded field: {0}'.format(field.python_coded_field))

        return python_coded_field.train_document_field_detector_model(document_type,
                                                                      field,
                                                                      train_data_project_ids,
                                                                      use_only_confirmed_field_values)

    @classmethod
    def detect_field_values(cls,
                            log: ProcessLogger,
                            doc: Document,
                            field: DocumentField) -> List[DetectedFieldValue]:
        python_coded_field = PYTHON_CODED_FIELDS_REGISTRY.get(field.python_coded_field)  # type: PythonCodedField
        if not python_coded_field:
            raise RuntimeError('Unknown python-coded field: {0}'.format(field.python_coded_field))
        field_type_adapter = FIELD_TYPES_REGISTRY[field.type]  # type: FieldType

        detected_values = list()  # type: List[DetectedFieldValue]
        if python_coded_field.by_sentence:
            qs_text_units = TextUnit.objects \
                .filter(document=doc) \
                .filter(unit_type=field.text_unit_type) \
                .order_by('location_start', 'pk')

            for text_unit in qs_text_units.iterator():
                for value, location_start, location_end in python_coded_field.get_values(text_unit.text) or []:
                    detected_values.append(
                        DetectedFieldValue(field, value, text_unit, None, location_start, location_end))
                    if not (field_type_adapter.multi_value or field.is_choice_field()):
                        return detected_values
        else:
            for value, location_start, location_end in python_coded_field.get_values(doc.full_text) or []:
                text_unit = TextUnit.objects.filter(document=doc,
                                                    unit_type='sentence',
                                                    location_start__lte=location_start,
                                                    location_end__gte=location_start).first()  # type: TextUnit
                if not text_unit:
                    raise RuntimeError('Python coded field {0} detected a value in document {1} at '
                                       'location [{2};{3}] but the start of location does not belong to any '
                                       'text unit object in DB.\n'
                                       'It can not be. Something is broken.'
                                       .format(field.python_coded_field, doc, location_start, location_end))
                location_length = location_end - location_start
                location_start = location_start - text_unit.location_start
                location_end = location_start + location_length
                detected_values.append(DetectedFieldValue(field, value, text_unit, None, location_start, location_end))
                if not (field_type_adapter.multi_value or field.is_choice_field()):
                    return detected_values

        return detected_values
