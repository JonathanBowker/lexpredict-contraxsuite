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

from typing import List
from apps.document.async_tasks.detect_field_values_task import DocDetectFieldValuesParams
from apps.users.models import User

__author__ = "ContraxSuite, LLC; LexPredict, LLC"
__copyright__ = "Copyright 2015-2019, ContraxSuite, LLC"
__license__ = "https://github.com/LexPredict/lexpredict-contraxsuite/blob/1.2.3/LICENSE"
__version__ = "1.2.3"
__maintainer__ = "LexPredict, LLC"
__email__ = "support@contraxsuite.com"


def run_detect_field_values_for_document(dcptrs: DocDetectFieldValuesParams,
                                         user: User = None):
    from apps.task.tasks import call_task_func
    from apps.document.tasks import DetectFieldValues
    call_task_func(DetectFieldValues.detect_field_values_for_document,
                   (dcptrs,),
                   user_id=user.pk if user else None,
                   visible=False)


def run_detect_field_values_as_sub_tasks(parent: 'ExtendedTask',
                                         document_ids: List[int],
                                         do_not_write: bool = False):
    from apps.document.tasks import DetectFieldValues
    from apps.document.fields_detection.detect_field_values_params import DocDetectFieldValuesParams
    args = [(DocDetectFieldValuesParams(document_id, do_not_write, False),)
            for document_id in document_ids]
    parent.run_sub_tasks('Detect Field Values',
                         DetectFieldValues.detect_field_values_for_document,
                         args)
