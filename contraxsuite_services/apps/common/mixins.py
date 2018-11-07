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
import datetime
import json
import operator
import os
import re
from functools import reduce

# Third-party imports
import pandas as pd
from rest_framework import serializers
from rest_framework.filters import BaseFilterBackend
from rest_framework.generics import ListAPIView
from rest_framework.response import Response

# Django imports
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields.jsonb import KeyTextTransform
from django.core.exceptions import FieldError
from django.core.paginator import Paginator, EmptyPage
from django.core.serializers.json import DjangoJSONEncoder
from django.core.urlresolvers import reverse
from django.db.models import Q, fields as django_fields
from django.db.models.expressions import OrderBy, Random, RawSQL, Ref
from django.db.models.sql.constants import ORDER_DIR
from django.db.models.sql.query import get_order_dir
from django.db.utils import DatabaseError
from django.http import JsonResponse
from django.views.generic import ListView
from django.views.generic.base import View
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import MultipleObjectMixin

# Project imports
from apps.common.models import Action
from apps.common.utils import cap_words, export_qs_to_file, download

__author__ = "ContraxSuite, LLC; LexPredict, LLC"
__copyright__ = "Copyright 2015-2018, ContraxSuite, LLC"
__license__ = "https://github.com/LexPredict/lexpredict-contraxsuite/blob/1.1.5/LICENSE"
__version__ = "1.1.5"
__maintainer__ = "LexPredict, LLC"
__email__ = "support@contraxsuite.com"


base_success_msg = '%s "%s" was successfully %s.'


class AdminRequiredMixin(PermissionRequiredMixin):
    raise_exception = True

    def has_permission(self):
        return not self.request.user.is_reviewer


class TechAdminRequiredMixin(PermissionRequiredMixin):
    raise_exception = True

    def has_permission(self):
        return self.request.user.is_admin


def get_model(self):
    model = None
    try:
        model = self.model
    except AttributeError:
        pass
    if not model:
        try:
            model = self.get_form_class()._meta.model
        except AttributeError:
            pass
    if not model:
        try:
            model = self.get_queryset().model
        except AttributeError:
            pass
    return model


class AddModelNameMixin(LoginRequiredMixin):
    """
    Add extra variables related with model into context.
    """
    def get_context_data(self, **kwargs):
        res = super().get_context_data(**kwargs)
        model = get_model(self)
        res['model_name'] = model._meta.verbose_name
        res['model_name_init'] = model._meta.model_name
        res['model_name_plural'] = model._meta.verbose_name_plural
        res['model_obj'] = model
        res['model_app'] = model._meta.app_label
        return res


class MessageMixin(object):
    """
    Pass custom success message in messages
    """
    def form_valid(self, form):
        response = super().form_valid(form)
        if hasattr(form, 'multiple_objects_created') and form.multiple_objects_created > 1:
            msg = '%d "%s" were created/updated successfully' % (
                form.multiple_objects_created,
                cap_words(self.object._meta.verbose_name_plural))
        else:
            msg = base_success_msg % (
                cap_words(self.object._meta.verbose_name),
                self.object.__str__(), self.success_message)
        messages.success(self.request, msg)
        return response


class TemplateNamesMixin(object):
    """
    Add "model_name_suffix.html" template name format (extra "_")
    """
    def get_template_names(self):
        if self.template_name is not None:
            return self.template_name
        names = super().get_template_names()
        model = get_model(self)
        app_label = model._meta.app_label
        template_name = '{}{}.html'.format(
            model._meta.verbose_name.replace(' ', '_'),
            self.template_name_suffix)
        names.append(os.path.join(app_label, template_name))
        names.append('{}{}.html'.format('base', self.template_name_suffix))
        return names


class SingleObjectMixin(MessageMixin, AddModelNameMixin, TemplateNamesMixin):
    pass


class CustomCreateView(AdminRequiredMixin, SingleObjectMixin, CreateView):
    success_message = 'created'

    def get_form_class(self):
        self.fields = self.get_fields()
        return super().get_form_class()

    def get_fields(self):
        return self.fields


class CustomUpdateView(CustomCreateView, UpdateView):
    success_message = 'updated'


class CustomDetailView(CustomUpdateView):
    """
    Detail view based on Update view to pass form in context
    and iterate over form fields with field names/labels
    """
    template_name_suffix = '_detail'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['fields'] = self.fields
        update_url = self.get_update_url()
        ctx['update_url'] = update_url
        # url = urllib.parse.urlparse(self.request.get_full_path())
        # ctx['edit_url'] = urllib.parse.urlunparse(
        #     (url.scheme, url.netloc, edit_url, url.params, url.query, url.fragment))
        return ctx

    def get_update_url(self):
        return reverse(
            '{}:{}-update'.format(
                self.model._meta.app_label,
                self.model._meta.verbose_name.replace(' ', '-')),
            args=[self.kwargs.get(self.slug_field, self.kwargs[self.pk_url_kwarg])])


class ReviewerQSMixin(MultipleObjectMixin):
    limit_reviewers_qs_by_field = None

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.user.is_reviewer and self.limit_reviewers_qs_by_field is not None:
            # limit qs for reviewers
            if isinstance(self.limit_reviewers_qs_by_field, (list, tuple)):
                lookup = {'%s__taskqueue__reviewers' % i: self.request.user for i in
                          self.limit_reviewers_qs_by_field}
            elif self.limit_reviewers_qs_by_field == "":
                lookup = {'taskqueue__reviewers': self.request.user}
            else:
                lookup = {
                    '%s__taskqueue__reviewers'
                    % self.limit_reviewers_qs_by_field: self.request.user}
            qs = qs.filter(**lookup)
        return qs


class BaseCustomListView(AddModelNameMixin, TemplateNamesMixin, ListView):
    paginate_by = 10
    export_params = dict(
        column_names=None,
        url_name=None,
        get_params=None
    )

    # handle "export" requests
    def get(self, request, *args, **kwargs):
        if 'export' in self.request.GET:
            return export_qs_to_file(
                request, qs=self.get_queryset(), **self.export_params)
        return super().get(request, *args, **kwargs)

    @staticmethod
    def filter(search_str, qs, _or_lookup,
               _and_lookup=None, _not_lookup=None):
        search_list = re.split(r'\s*,\s*', search_str.strip().strip(","))
        _not_search_list = [i[1:].strip() for i in search_list if i.startswith('-')]
        _and_search_list = [i[1:].strip() for i in search_list if i.startswith('&')]
        _or_search_list = [i for i in search_list if i[0] not in ['-', '&']]

        if _or_search_list:
            query = reduce(
                operator.or_,
                (Q(**{_or_lookup: i}) for i in _or_search_list))
            qs = qs.filter(query)
        if _and_search_list:
            query = reduce(
                operator.and_,
                (Q(**{_and_lookup or _or_lookup: i}) for i in _and_search_list))
            qs = qs.filter(query)
        if _not_search_list:
            query = reduce(
                operator.or_,
                (Q(**{_not_lookup or _or_lookup: i}) for i in _not_search_list))
            qs = qs.exclude(query)
        return qs


class CustomListView(ReviewerQSMixin, BaseCustomListView):
    pass


class CustomDeleteView(AddModelNameMixin, PermissionRequiredMixin, DeleteView):
    template_name = 'base_delete.html'
    raise_exception = True

    def handle_no_permission(self):
        if self.request.is_ajax():
            data = {'message': 'Permission denied.', 'level': 'error'}
            return JsonResponse(data, encoder=DjangoJSONEncoder, safe=False)
        return super().handle_no_permission()

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            return JsonResponse(str(self.get_object()), encoder=DjangoJSONEncoder, safe=False)
        return super().get(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        msg = base_success_msg % (
            cap_words(obj._meta.verbose_name),
            obj.__str__(), 'deleted')
        if request.is_ajax():
            obj.delete()
            data = {'message': msg, 'level': 'success'}
            return JsonResponse(data, encoder=DjangoJSONEncoder, safe=False)
        messages.success(request, msg)
        return super().post(request, *args, **kwargs)


class AjaxResponseMixin(object):

    def render_to_response(self, *args, **kwargs):
        if self.request.is_ajax():
            data = self.get_json_data(**kwargs)
            return JsonResponse(data, encoder=DjangoJSONEncoder, safe=False)
        return super().render_to_response(*args, **kwargs)


class JSONResponseView(View):

    def response(self, request, *args, **kwargs):
        data = self.get_json_data(request, *args, **kwargs)
        return JsonResponse(data, encoder=DjangoJSONEncoder, safe=False)

    def get(self, request, *args, **kwargs):
        return self.response(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.response(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.response(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.response(request, *args, **kwargs)

    def get_json_data(self, request, *args, **kwargs):
        return []


class TypeaheadView(ReviewerQSMixin, JSONResponseView):

    def get_json_data(self, request, *args, **kwargs):
        qs = self.model.objects.all()
        if "q" in request.GET:
            search_key = '%s__icontains' % self.search_field
            qs = qs.filter(**{search_key: request.GET.get("q")})\
                .order_by(self.search_field).distinct(self.search_field)
        return self.qs_to_values(qs)

    def qs_to_values(self, qs):
        return [{"value": i} for i in qs.values_list(self.search_field, flat=True)]


class SubmitView(JSONResponseView):
    error_message = 'Error'
    success_message = 'Success'

    def response(self, request, *args, **kwargs):
        try:
            data = self.process(request)
        except:
            data = self.failure()
        return JsonResponse(data, encoder=DjangoJSONEncoder, safe=False)

    def get_success_message(self):
        return self.success_message

    def get_error_message(self):
        return self.error_message

    def failure(self):
        return {'message': self.get_error_message(), 'status': 'error'}

    def success(self, data=None):
        ret = {'message': self.get_success_message(), 'status': 'success'}
        if data is not None:
            ret.update(data)
        return ret


class AjaxListView(ReviewerQSMixin, AjaxResponseMixin, BaseCustomListView):
    json_fields = []
    extra_json_fields = []
    annotate = {}

    # TODO: remove duplication with BaseCustomListView
    # handle "export" requests
    def get(self, request, *args, **kwargs):
        if 'export' in self.request.GET:
            return export_qs_to_file(
                request, qs=self.get_queryset(), **self.export_params)
        if request.GET.get('export_to') in ['csv', 'xlsx', 'pdf']:
            data = self.get_json_data()
            if isinstance(data, dict) and 'data' in data:
                data = data['data']
            return self.export(data,
                               source_name=self.get_export_file_name() or
                                           self.get_queryset().model.__name__.lower(),
                               fmt=request.GET.get('export_to'))

        if not request.is_ajax():
            self.object_list = []
            context = self.get_context_data()
            return self.render_to_response(context)
        return self.render_to_response()

    def get_json_data(self, **kwargs):
        qs = kwargs.get('qs')
        if qs is None:
            qs = self.get_queryset()
        extra_json_fields = list(self.extra_json_fields)
        extra_json_fields.append('pk')
        extra_json_fields += list(self.annotate.keys())
        if not self.json_fields:
            self.json_fields = [f.name for f in self.model._meta.concrete_fields]
        data = list(qs.annotate(**self.annotate)
                    .values(*(self.json_fields + extra_json_fields)))

        # TODO: consider replace none_to_bool - either use default=False or update jqWidgets
        bool_fields = [i.name for i in self.model._meta.fields
                       if isinstance(i, django_fields.BooleanField)]
        for row in data:
            row.update((k, False) for k, v in row.items() if v is None and k in bool_fields)
            if not kwargs.get('keep_tags'):
                row.update((k, v.replace("<", "&lt;").replace(">", "&gt;"))
                           for k, v in row.items() if isinstance(v, str))

        return data

    def export(self, data, source_name, fmt='csv'):
        data = self.process_export_data(data)
        return download(data, fmt, file_name=source_name)

    def process_export_data(self, data):
        return data

    def get_export_file_name(self):
        return


class JqPaginatedListView(AjaxListView):
    conditions = dict(EQUAL='iexact',
                      EQUAL_CASE_SENSITIVE='exact',
                      CONTAINS='icontains',
                      CONTAINS_CASE_SENSITIVE='contains',
                      LESS_THAN='lt',
                      LESS_THAN_OR_EQUAL='lte',
                      GREATER_THAN='gt',
                      GREATER_THAN_OR_EQUAL='gte',
                      STARTS_WITH='istartswith',
                      ENDS_WITH='iendswith',
                      STARTS_WITH_CASE_SENSITIVE='startswith',
                      ENDS_WITH_CASE_SENSITIVE='endswith')
    conditions_empty = dict(EMPTY=('exact', ''),
                            NULL=('isnull', True),
                            NOT_NULL=('isnull', False))
    conditions_neg = dict(DOES_NOT_CONTAIN='icontains',
                          DOES_NOT_CONTAIN_CASE_SENSITIVE='contains',
                          NOT_EQUAL='exact')
    field_types = dict()
    unique_field = 'pk'

    def get_field_types(self):
        return self.field_types

    def filter_and_sort(self, qs):
        """
        Filter and sort data on server side.
        """
        qs = self.filter(qs)

        qs = self.sort(qs)

        return qs

    def filter(self, qs):
        filterscount = int(self.request.GET.get('filterscount', 0))
        # server-side filtering
        if filterscount:
            filters = dict()
            for filter_num in range(filterscount):
                num = str(filter_num)
                field = self.request.GET.get('filterdatafield' + num).replace('-', '_')
                value = (self.get_field_types() or self.field_types).get(field, str)(
                    self.request.GET.get('filtervalue' + num))
                condition = self.request.GET.get('filtercondition' + num)
                op = int(self.request.GET.get('filteroperator' + num, 0))
                if not filters.get(field):
                    filters[field] = list()
                filters[field].append(
                    dict(value=value, condition=condition, operator=op)
                )
            for field in filters:
                q_prev = q_curr = Q()
                op = None
                for field_condition in filters[field]:
                    cond = field_condition['condition']
                    val = field_condition['value']
                    op = field_condition['operator']

                    # TODO: check if bool/null filter improved in new jqWidgets grid
                    # if vale is False filter None and False
                    if (self.get_field_types() or
                            self.field_types).get(field, str).__name__ == 'bool_lookup':
                        if cond == 'NOT_EQUAL' and val is True or cond == 'EQUAL' and val is False:
                            q_curr = Q(**{field: False}) | Q(**{'%s__isnull' % field: True})
                        else:
                            q_curr = Q(**{field: True})
                    elif cond in self.conditions:
                        cond_str = '%s__%s' % (field, self.conditions[cond])
                        q_curr = Q(**{cond_str: val})
                    elif cond in self.conditions_empty:
                        cond_str = '%s__%s' % (field, self.conditions_empty[cond][0])
                        val = self.conditions_empty[cond][1]
                        q_curr = Q(**{cond_str: val})
                    elif cond in self.conditions_neg:
                        cond_str = '%s__%s' % (field, self.conditions_neg[cond])
                        q_curr = ~Q(**{cond_str: val})
                    # filter out empty and None values as well
                    elif cond == 'NOT_EMPTY':
                        q_curr = ~Q(**{field: ''}) & Q(**{'%s__isnull' % field: False})
                    # one field can have 2 conditions maximum
                    if not q_prev:
                        q_prev = q_curr
                        q_curr = Q()
                qs = qs.filter(q_prev | q_curr) if op else qs.filter(q_prev & q_curr)
        return qs

    def sort(self, qs):
        # server-side sorting
        sortfield = self.request.GET.get('sortdatafield')
        sortorder = self.request.GET.get('sortorder', 'asc')
        if sortfield:
            sortfield = sortfield.replace('-', '_')
            if sortorder == 'desc':
                qs = qs.order_by('-%s' % sortfield)
            elif sortorder == 'asc':
                qs = qs.order_by(sortfield)
        return qs

    def paginate(self, qs):
        # server-side pagination
        page = self.request.GET.get('pagenum')
        size = self.request.GET.get('pagesize')
        paginator = Paginator(qs, size)
        try:
            pg = paginator.page(int(page) + 1)
        except ValueError:
            # If page is not an integer, deliver first page.
            pg = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            return []
            # pg = paginator.page(paginator.num_pages)

        # TODO: figure out why those 3 lines below were used before
        # qs = qs.filter(
        #     **{'%s__in' % self.unique_field: [getattr(obj, self.unique_field) if hasattr(obj, self.unique_field) else obj[self.unique_field]
        #                                       for obj in pg.object_list]})
        # return qs
        return pg.object_list

    def get_json_data(self, **kwargs):
        data = []
        qs = self.get_queryset()    # .distinct()
        total_records = qs.count()
        enable_pagination = json.loads(self.request.GET.get('enable_pagination', 'null'))
        export_to = self.request.GET.get('export_to')
        qs = self.filter_and_sort(qs)
        if export_to or not enable_pagination:
            data = super().get_json_data(qs=qs, **kwargs)
        elif qs.exists():
            total_records = qs.count()
            qs = self.paginate(qs)
            data = super().get_json_data(qs=qs, **kwargs)
        return {'data': data, 'total_records': total_records}

    @staticmethod
    def date_lookup(value):
        """
        Allows to input date in 'mm-dd-yyyy' format
        """
        try:
            res = datetime.datetime.strptime(value, '%m-%d-%Y').strftime('%Y-%m-%d')
        except ValueError:
            res = value
        return res

    @staticmethod
    def bool_lookup(value):
        rel = {'1': True, 'true': True, 'True': True, 'good': True, 'Good': True,
               '0': False, 'false': False, 'False': False, 'bad': False, 'Bad': False,
               'none': None, 'None': None, 'null': None, 'Null': None}
        ret_value = rel.get(value, '')
        return ret_value


class SimpleRelationSerializer(serializers.ModelSerializer):
    """
    Serializer that extracts nested relations as char field
    """

    def get_fields(self):
        for field in self.Meta.fields:
            if '__' in field:
                self._declared_fields[field] = serializers.CharField(
                    source='.'.join(field.split('__')),
                    read_only=True)
        return super().get_fields()


class JqFilterBackend(BaseFilterBackend):

    def filter_queryset(self, request, queryset, *args):
        jq_view = JqPaginatedListView(request=request)
        if 'sortdatafield' in request.GET or 'filterscount' in request.GET:
            queryset = jq_view.filter_and_sort(queryset)
        enable_pagination = json.loads(request.GET.get('enable_pagination', 'null'))
        if enable_pagination and 'pagenum' in request.GET:
            queryset = jq_view.paginate(queryset)
        return queryset


class ModelFieldFilterBackend(BaseFilterBackend):

    def filter_queryset(self, request, queryset, *args):
        for param_name, param_value in request.GET.items():
            try:
                if param_name.endswith('_contains'):
                    param_name = param_name.replace('_contains', '__icontains')
                queryset = queryset.filter(**{param_name: param_value})
            except FieldError:
                continue
        return queryset


class JqListAPIMixin(object):
    """
    Filter, sort and paginate queryset using jqWidgets' grid GET params
    return {'data': [.....], 'total_records': N}
    """
    extra_data = None

    def filter_queryset(self, queryset):
        jq_view = JqPaginatedListView(request=self.request)
        if 'sortdatafield' in self.request.GET or 'filterscount' in self.request.GET:
            queryset = jq_view.filter_and_sort(queryset)
        return queryset

    def paginate_queryset(self, queryset):
        jq_view = JqPaginatedListView(request=self.request)
        enable_pagination = json.loads(self.request.GET.get('enable_pagination', 'null'))
        if enable_pagination and 'pagenum' in self.request.GET:
            queryset = jq_view.paginate(queryset)
        return queryset

    def list(self, request, *args, **kwargs):
        # 1. get full queryset
        queryset = self.get_queryset()
        # 2. filter and sort
        queryset = self.filter_queryset(queryset)
        # 2.1 export in xlsx if needed
        if request.GET.get('export_to') in ['csv', 'xlsx', 'pdf']:
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data
            return self.export(data,
                               source_name=self.get_export_file_name() or
                                           queryset.model.__name__.lower(),
                               fmt=request.GET.get('export_to'))
        # 3. count total records !before queryset paginated
        try:
            total_records = queryset.count()
        except:
            total_records = len(queryset)
        # 4. get extra data !before queryset paginated
        extra_data = self.get_extra_data(queryset)
        # 5. paginate
        queryset = self.paginate_queryset(queryset)
        # 6. serialize
        serializer = self.get_serializer(queryset, many=True)
        # 7. compose returned data
        show_total_records = json.loads(self.request.GET.get('total_records', 'false'))
        if show_total_records:
            ret = {'data': serializer.data,
                   'total_records': total_records}
            if extra_data:
                ret.update(extra_data)
            return Response(ret)
        return Response(serializer.data)

    def get_extra_data(self, queryset):
        return self.extra_data or {}

    def export(self, data, source_name, fmt='xlsx'):
        data = pd.DataFrame(data).fillna('')
        data = self.process_export_data(data)
        return download(data, fmt, file_name=source_name)

    def get_export_file_name(self):
        pass

    def process_export_data(self, data):
        return data


class JqListAPIView(JqListAPIMixin, ListAPIView):
    """
    Filter, sort and paginate queryset using jqWidgets' grid GET params
    """
    pass


class TypeaheadAPIView(ReviewerQSMixin, ListAPIView):

    def get(self, request, *args, **kwargs):
        field_name = self.kwargs.get('field_name')
        try:
            _ = self.model._meta.get_field(field_name)
        except:
            raise RuntimeError('Wrong field name "{}" for model "{}"'.format(
                field_name, self.model.__name__))
        qs = self.model.objects.all()
        if "q" in request.GET:
            search_key = '%s__icontains' % field_name
            qs = qs.filter(**{search_key: request.GET.get("q")})\
                .order_by(field_name).distinct(field_name)
        return JsonResponse(self.qs_to_values(qs, field_name), encoder=DjangoJSONEncoder, safe=False)

    def qs_to_values(self, qs, field_name):
        return [{"value": i} for i in qs.values_list(field_name, flat=True)]


class NestedKeyTextTransform(KeyTextTransform):
    """
    Create annotation for nested json fields.
    F.e. for field like "metadata__level1__level2":
    >>> NestedKeyTextTransform(['level1', 'level2'], 'metadata')
    >>> NestedKeyTextTransform(['level1', 'level2'], 'metadata', output_field=FloatField())
    """
    def __init__(self, nested_key_names, *args, **kwargs):
        super().__init__(nested_key_names, *args, **kwargs)
        self.nested_key_names = nested_key_names
        self.nested_operator = '#>>'
        self._output_field = kwargs.get('output_field') or self._output_field

    def as_sql(self, compiler, connection):
        """
        Postgres specific way to cast data type!
        f.e. see django/db/models/functions/base.py:Cast
        """
        lhs, params = compiler.compile(self.lhs)
        return "(%s %s %%s)::%s" % (lhs, self.nested_operator,
                                    self._output_field.db_type(connection)),\
               [self.nested_key_names] + params


class APIActionMixin(object):
    """
    Mixin class to track user activity in Action model
    """
    user_action_methods = dict(
        POST='create',
        PUT='update',
        PATCH='update',
        GET='detail'
    )
    user_action = None

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        user_action_name = self.get_action_name()
        if not user_action_name:
            user_action_name = self.user_action_methods.get(request.method)
        if (self.lookup_url_kwarg or self.lookup_field) in self.kwargs:
            user_action_object = self.get_object()
        else:
            user_action_object = None
            if request.method == 'GET':
                user_action_name = 'list'
        model = self.queryset.model
        content_type = ContentType.objects.get_for_model(model)
        user_action = Action.objects.create(
            user=request.user,
            name=user_action_name,
            content_type=content_type
        )
        if user_action_object:
            user_action.object = user_action_object
            user_action.save()
        self.user_action = user_action
        return response

    def perform_create(self, serializer):
        obj = serializer.save()
        if self.user_action is not None:
            self.user_action.object = obj
            self.user_action.save()
        return obj

    def get_action_name(self):
        """
        Helper to define custom action name
        """
        pass


def get_group_by(self, select, order_by):
    """
    See original get_group_by at django.db.models.sql.compiler>SQLCompiler
    """
    if self.query.group_by is None:
        return []
    expressions = []
    if self.query.group_by is not True:
        for expr in self.query.group_by:
            if not hasattr(expr, 'as_sql'):
                expressions.append(self.query.resolve_ref(expr))
            else:
                expressions.append(expr)
    for expr, _, _ in select:
        cols = expr.get_group_by_cols()
        for col in cols:
            expressions.append(col)
    for expr, (sql, params, is_ref) in order_by:
        if expr.contains_aggregate:
            continue
        if is_ref:
            continue
        expressions.extend(expr.get_source_expressions())
    having_group_by = self.having.get_group_by_cols() if self.having else ()
    for expr in having_group_by:
        expressions.append(expr)
    result = []
    # changed from set() to []
    seen = []
    expressions = self.collapse_group_by(expressions, having_group_by)

    for expr in expressions:
        sql, params = self.compile(expr)
        if (sql, tuple(params)) not in seen:
            result.append((sql, params))
            # changed from add to append
            seen.append((sql, tuple(params)))
    return result


def get_order_by(self):
    """
    See original get_group_by at django.db.models.sql.compiler>SQLCompiler
    """
    if self.query.extra_order_by:
        ordering = self.query.extra_order_by
    elif not self.query.default_ordering:
        ordering = self.query.order_by
    else:
        ordering = (self.query.order_by or self.query.get_meta().ordering or [])
    if self.query.standard_ordering:
        asc, desc = ORDER_DIR['ASC']
    else:
        asc, desc = ORDER_DIR['DESC']

    order_by = []
    for field in ordering:
        if hasattr(field, 'resolve_expression'):
            if not isinstance(field, OrderBy):
                field = field.asc()
            if not self.query.standard_ordering:
                field.reverse_ordering()
            order_by.append((field, False))
            continue
        if field == '?':  # random
            order_by.append((OrderBy(Random()), False))
            continue

        col, order = get_order_dir(field, asc)
        descending = True if order == 'DESC' else False

        if col in self.query.annotation_select:
            # Reference to expression in SELECT clause
            order_by.append((
                OrderBy(Ref(col, self.query.annotation_select[col]), descending=descending),
                True))
            continue
        if col in self.query.annotations:
            # References to an expression which is masked out of the SELECT clause
            order_by.append((
                OrderBy(self.query.annotations[col], descending=descending),
                False))
            continue

        if '.' in field:
            # This came in through an extra(order_by=...) addition. Pass it
            # on verbatim.
            table, col = col.split('.', 1)
            order_by.append((
                OrderBy(
                    RawSQL('%s.%s' % (self.quote_name_unless_alias(table), col), []),
                    descending=descending
                ), False))
            continue

        if not self.query._extra or col not in self.query._extra:
            # 'col' is of the form 'field' or 'field1__field2' or
            # '-field1__field2__field', etc.
            order_by.extend(self.find_ordering_name(
                field, self.query.get_meta(), default_order=asc))
        else:
            if col not in self.query.extra_select:
                order_by.append((
                    OrderBy(RawSQL(*self.query.extra[col]), descending=descending),
                    False))
            else:
                order_by.append((
                    OrderBy(Ref(col, RawSQL(*self.query.extra[col])), descending=descending),
                    True))
    result = []
    # changed from set() to []
    seen = []

    for expr, is_ref in order_by:
        if self.query.combinator:
            src = expr.get_source_expressions()[0]
            # Relabel order by columns to raw numbers if this is a combined
            # query; necessary since the columns can't be referenced by the
            # fully qualified name and the simple column names may collide.
            for idx, (sel_expr, _, col_alias) in enumerate(self.select):
                if is_ref and col_alias == src.refs:
                    src = src.source
                elif col_alias:
                    continue
                if src == sel_expr:
                    expr.set_source_expressions([RawSQL('%d' % (idx + 1), ())])
                    break
            else:
                raise DatabaseError('ORDER BY term does not match any column in the result set.')
        resolved = expr.resolve_expression(
            self.query, allow_joins=True, reuse=None)
        sql, params = self.compile(resolved)
        # Don't add the same column twice, but the order direction is
        # not taken into account so we strip it. When this entire method
        # is refactored into expressions, then we can check each part as we
        # generate it.
        without_ordering = self.ordering_parts.search(sql).group(1)
        if (without_ordering, tuple(params)) in seen:
            continue
        # changed from add to append
        seen.append((without_ordering, tuple(params)))
        result.append((resolved, (sql, params, is_ref)))
    return result


from django.db.models.sql.compiler import SQLCompiler
SQLCompiler.get_group_by = get_group_by
SQLCompiler.get_order_by = get_order_by
