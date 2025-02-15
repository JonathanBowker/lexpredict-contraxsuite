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

from typing import Dict, Any, Optional

import django.dispatch

from apps.common.log_utils import ProcessLogger
from apps.document.models import Document
from apps.users.models import User

__author__ = "ContraxSuite, LLC; LexPredict, LLC"
__copyright__ = "Copyright 2015-2019, ContraxSuite, LLC"
__license__ = "https://github.com/LexPredict/lexpredict-contraxsuite/blob/1.2.3/LICENSE"
__version__ = "1.2.3"
__maintainer__ = "LexPredict, LLC"
__email__ = "support@contraxsuite.com"


document_changed = django.dispatch.Signal(providing_args=['changed_by_user', 'log', 'document', 'system_fields_changed',
                                                          'generic_fields_changed', 'user_fields_changed',
                                                          'pre_detected_field_values', 'document_initial_load'])
document_deleted = django.dispatch.Signal(providing_args=['user', 'document'])

document_field_changed = django.dispatch.Signal(providing_args=['user', 'document_field'])
document_field_deleted = django.dispatch.Signal(providing_args=['user', 'document_field'])

document_type_changed = django.dispatch.Signal(providing_args=['user', 'document_type'])
document_type_deleted = django.dispatch.Signal(providing_args=['user', 'document_type'])

doc_soft_delete = django.dispatch.Signal(providing_args=['document_ids', 'delete_pending'])

doc_update_documents_assignees = django.dispatch.Signal(providing_args=['documents', 'assignee_id', 'changed_by_user'])

cache_doc_fields_task = django.dispatch.Signal(providing_args=['documents', 'status_name', 'changed_by_user'])


def fire_document_changed(sender,
                          log: ProcessLogger,
                          document: Document,
                          changed_by_user: User = None,
                          document_initial_load: bool = False,
                          system_fields_changed: bool = True,
                          generic_fields_changed: bool = True,
                          user_fields_changed: bool = True,
                          pre_detected_field_values: Optional[Dict[str, Any]] = None):
    document_changed.send(sender,
                          log=log,
                          changed_by_user=changed_by_user,
                          document_initial_load=document_initial_load,
                          document=document,
                          system_fields_changed=system_fields_changed,
                          user_fields_changed=user_fields_changed,
                          generic_fields_changed=generic_fields_changed,
                          pre_detected_field_values=pre_detected_field_values)


def fire_documents_changed(sender,
                           log: ProcessLogger,
                           doc_qr,
                           changed_by_user: User = None,
                           document_initial_load: bool = False,
                           system_fields_changed: bool = True,
                           generic_fields_changed: bool = True,
                           user_fields_changed: bool = True):
    for doc in doc_qr.select_related('document_type', 'project', 'status'):  # type: Document
        fire_document_changed(sender=sender,
                              log=log,
                              changed_by_user=changed_by_user,
                              document_initial_load=document_initial_load,
                              document=doc,
                              system_fields_changed=system_fields_changed,
                              generic_fields_changed=generic_fields_changed,
                              user_fields_changed=user_fields_changed)


def fire_document_deleted(sender,
                          document: Document,
                          user: User):
    document_deleted.send(sender,
                          user=user,
                          document=document)


def fire_doc_soft_delete(sender,
                         document_ids,
                         delete_pending: bool):
    doc_soft_delete.send(sender,
                         document_ids=document_ids,
                         delete_pending=delete_pending)


def fire_doc_update_documents_assignees(sender,
                                        documents,
                                        assignee_id: int,
                                        changed_by_user: User):
    doc_update_documents_assignees.send(sender,
                                        documents=documents,
                                        assignee_id=assignee_id,
                                        changed_by_user=changed_by_user)


def fire_cache_doc_fields_task(sender,
                               documents,
                               status_name: str,
                               changed_by_user: User):
    cache_doc_fields_task.send(sender,
                               documents=documents,
                               status_name=status_name,
                               changed_by_user=changed_by_user)
