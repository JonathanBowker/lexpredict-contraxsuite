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

from typing import List, Dict
from django.db import connection
from apps.common.model_utils.table_deps import TableDeps

__author__ = "ContraxSuite, LLC; LexPredict, LLC"
__copyright__ = "Copyright 2015-2019, ContraxSuite, LLC"
__license__ = "https://github.com/LexPredict/lexpredict-contraxsuite/blob/1.2.3/LICENSE"
__version__ = "1.2.3"
__maintainer__ = "LexPredict, LLC"
__email__ = "support@contraxsuite.com"


class ModelBulkDelete:
    def __init__(self, deps: List[TableDeps]):
        # records like
        # document_documentnote.field_value_id -> document_documentfieldvalue.id,
        #   document_documentfieldvalue.text_unit_id -> document_textunit.id,
        #   document_textunit.document_id -> document_document.id
        self.deps = deps
        self.table_name = deps[0].deps[-1].ref_table
        self.key_column = deps[0].deps[-1].ref_table_pk

    def build_get_deleted_count_queries(self) -> List[str]:
        # dep like
        # "pk:[id], document_documentfieldvalue.text_unit_id -> document_textunit.id, document_textunit.document_id -> document_document.id"
        # will produce
        # SELECT COUNT(*) FROM "document_documentfieldvalue"
        #   JOIN "document_textunit" ON "document_textunit"."id" = "document_documentfieldvalue"."text_unit_id"
        #   JOIN "document_document" ON "document_document"."id" = "document_textunit":"document_id"
        # + (optionally):
        #   WHERE "document_document"."id" = {id}
        queries = []  # type: List[str]

        for dep in self.deps:
            query = f'SELECT COUNT(*) FROM "{dep.deps[0].own_table}"'
            for d in dep.deps:
                query += f'\n  INNER JOIN "{d.ref_table}" ON "{d.ref_table}"."{d.ref_table_pk}"' +\
                         f' = "{d.own_table}"."{d.ref_key}"'

            queries.append(query)

        return queries

    def build_delete_all_queries(self) -> List[str]:
        queries = []  # type: List[str]
        # TODO: wont work for composite primary keys
        for dep in self.deps:
            query = f'DELETE FROM "{dep.deps[0].own_table}"'
            query += f'\n  WHERE "{dep.deps[0].own_table}"."{dep.own_table_pk[0]}" IN'
            query += f'\n (SELECT "{dep.deps[0].own_table}"."{dep.own_table_pk[0]}" FROM "{dep.deps[0].own_table}"'
            for d in dep.deps:
                query += f'\n    JOIN "{d.ref_table}" ON "{d.ref_table}"."{d.ref_table_pk}"' + \
                         f' = "{d.own_table}"."{d.ref_key}"'
            queries.append(query)
        return queries

    def calculate_total_objects_to_delete(self, where_suffix: str) -> Dict[str, int]:
        count_to_del = {}  # type: Dict[str, int]
        queries = self.build_get_deleted_count_queries()
        with connection.cursor() as cursor:
            for i in range(len(self.deps)):
                cursor.execute(queries[i] + ' ' + where_suffix)
                row = cursor.fetchone()
                count = row[0]
                table_name = self.deps[i].deps[0].own_table
                count_to_del[table_name] = count
        return count_to_del

    def delete_objects(self, where_suffix: str) -> Dict[str, int]:
        count_deleted = {}  # type: Dict[str, int]
        queries = self.build_delete_all_queries()
        with connection.cursor() as cursor:
            cursor.db.autocommit = True
            for i in range(len(self.deps)):
                query = queries[i] + ' ' + where_suffix
                cursor.execute(query)
                count = cursor.rowcount
                table_name = self.deps[i].deps[0].own_table
                count_deleted[table_name] = count
        return count_deleted
