"""
    Copyright (C) 2017, ContraxSuite, LLC

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    You can also be released from the requirements of the license by purchasing
    a commercial license from ContraxSuite, LLC. Buying such a license is
    mandatory as soon as you develop commercial activities involving ContraxSuite
    software without disclosing the source code of your own applications.  These
    activities include: offering paid services to customers as an ASP or "cloud"
    provider, processing documents on the fly in a web application,
    or shipping ContraxSuite within a closed source product.
"""
# -*- coding: utf-8 -*-

# Standard imports
from collections import Iterable
from typing import Dict, Any, List, Optional

# Django imports
from django.contrib.postgres.aggregates.general import StringAgg
from django.db.models import Min, Max

from apps.common.log_utils import ProcessLogger
from apps.document import signals
# Project imports
from apps.document.field_types import FieldType
from apps.document.fields_detection.fields_detection_abstractions import DetectedFieldValue
from apps.document.fields_processing.field_processing_utils import merge_detected_field_values_to_python_value
from apps.document.models import DocumentField, Document, DocumentType
from apps.extract.models import CurrencyUsage
from apps.users.models import User

__author__ = "ContraxSuite, LLC; LexPredict, LLC"
__copyright__ = "Copyright 2015-2019, ContraxSuite, LLC"
__license__ = "https://github.com/LexPredict/lexpredict-contraxsuite/blob/1.2.3/LICENSE"
__version__ = "1.2.3"
__maintainer__ = "LexPredict, LLC"
__email__ = "support@contraxsuite.com"


def cache_field_values(doc: Document,
                       suggested_field_values: Optional[List[DetectedFieldValue]],
                       save: bool = True,
                       log: ProcessLogger = None,
                       changed_by_user: User = None,
                       system_fields_changed: bool = False,
                       generic_fields_changed: bool = False,
                       document_initial_load: bool = False) -> Dict[str, Any]:
    """
    Loads DocumentFieldValue objects from DB, merges them to get python field values of their fields for the document,
    converts them to the sortable DB-aware form and saves them to Document.f i eld_values.
    :param doc:
    :param save:
    :param suggested_field_values:
    :param log
    :param changed_by_user
    :param system_fields_changed
    :param generic_fields_changed
    :param document_initial_load
    :return:
    """
    document_type = doc.document_type  # type: DocumentType
    # TODO: get/save field value for specific field
    all_fields = list(document_type.fields.all())

    related_info_field_uids = {f.uid for f in all_fields if f.is_related_info_field()}

    fields_to_field_values = {f: None for f in all_fields}

    for fv in doc.documentfieldvalue_set.all():
        if fv.removed_by_user:
            continue

        field = fv.field
        field_type = fv.field.get_field_type()  # type: FieldType
        fields_to_field_values[field] = field_type \
            .merge_multi_python_values(fields_to_field_values.get(field), fv.python_value)

    field_uids_to_field_values_db = {}

    for f in all_fields:  # type: DocumentField
        field_type = f.get_field_type()  # type: FieldType
        v = fields_to_field_values[f]
        field_uids_to_field_values_db[f.uid] = field_type.merged_python_value_to_db(v)

    if suggested_field_values:
        field_codes_to_suggested_values = \
            merge_detected_field_values_to_python_value(suggested_field_values)  # type: Dict[str, Any]
    else:
        field_codes_to_suggested_values = None

    for f in all_fields:  # type: DocumentField
        field_type = f.get_field_type()  # type: FieldType
        if f.is_detectable():
            suggested_field_uid = Document.get_suggested_field_uid(f.uid)
            if field_codes_to_suggested_values:
                suggested_value_db = field_type.merged_python_value_to_db(field_codes_to_suggested_values.get(f.code))
            else:
                suggested_value_db = field_uids_to_field_values_db.get(suggested_field_uid)

            # suggested_value_db can be list, None or int, Iterable validation should be here
            if isinstance(suggested_value_db, Iterable) and f.is_related_info_field():
                suggested_value_db = len(suggested_value_db)
            field_uids_to_field_values_db[suggested_field_uid] = suggested_value_db

    if save:
        signals.fire_document_changed(sender=cache_field_values,
                                      changed_by_user=changed_by_user,
                                      log=log,
                                      document=doc,
                                      system_fields_changed=system_fields_changed,
                                      generic_fields_changed=generic_fields_changed,
                                      user_fields_changed=True,
                                      pre_detected_field_values=field_codes_to_suggested_values,
                                      document_initial_load=document_initial_load)

    return field_uids_to_field_values_db


def get_generic_values(doc: Document) -> Dict[str, Any]:
    # If changing keys of the returned dictionary - please change field code constants
    # in apps/rawdb/field_value_tables.py accordingly (_FIELD_CODE_CLUSTER_ID and others)

    document_qs = Document.all_objects.filter(pk=doc.pk) \
        .annotate(cluster_id=Max('documentcluster'),
                  parties=StringAgg('textunit__partyusage__party__name',
                                    delimiter=', ',
                                    distinct=True),
                  min_date=Min('textunit__dateusage__date'),
                  max_date=Max('textunit__dateusage__date'))

    # if a Document was suddenly removed to this time
    if not document_qs.exists():
        raise Document.DoesNotExist

    values = document_qs.values('cluster_id', 'parties', 'min_date',
                                'max_date').first()  # type: Dict[str, Any]

    max_currency = CurrencyUsage.objects.filter(text_unit__document_id=doc.id) \
        .order_by('-amount').values('currency', 'amount').first()  # type: Dict[str, Any]
    values['max_currency'] = max_currency
    values['max_currency_name'] = max_currency['currency'] if max_currency else None
    values['max_currency_amount'] = max_currency['amount'] if max_currency else None

    return values


def cache_generic_values(doc: Document, save: bool = True,
                         log: ProcessLogger = None,
                         fire_doc_changed_event: bool = True):
    if save:
        if fire_doc_changed_event:
            signals.fire_document_changed(sender=cache_generic_values,
                                          log=log,
                                          document=doc,
                                          system_fields_changed=False,
                                          generic_fields_changed=True,
                                          user_fields_changed=False,
                                          pre_detected_field_values=None)
