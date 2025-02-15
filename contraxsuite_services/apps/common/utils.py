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
import importlib
import io
import random
import re
import uuid

# Third-party imports
import django_excel as excel
import pandas as pd
import pdfkit as pdf
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML

# Django imports
from django.conf import settings
from django.conf.urls import url
from django.urls import reverse
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from django.utils.text import slugify
from django.utils import numberformat

# App imports
from apps.users.models import User, Role

__author__ = "ContraxSuite, LLC; LexPredict, LLC"
__copyright__ = "Copyright 2015-2019, ContraxSuite, LLC"
__license__ = "https://github.com/LexPredict/lexpredict-contraxsuite/blob/1.2.3/LICENSE"
__version__ = "1.2.3"
__maintainer__ = "LexPredict, LLC"
__email__ = "support@contraxsuite.com"


class CustomDjangoJSONEncoder(DjangoJSONEncoder):
    """
    JSONEncoder subclass that knows how to encode unusual objects.
    """
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return super().default(obj)


class Map(dict):
    """
    Class that converts dict into class-like object with access to its values via .key
    Example:
    m = Map({'first_name': 'Eduardo'}, last_name='Pool', age=24, sports=['Soccer'])
    print(m.first_name, m.age)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for arg in args:
            if isinstance(arg, dict):
                for k, v in arg.items():
                    self[k] = v

        if kwargs:
            for k, v in kwargs.items():
                self[k] = v

    def __getattr__(self, attr):
        return self.get(attr)

    def __setattr__(self, key, value):
        self.__setitem__(key, value)

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.__dict__.update({key: value})

    def __delattr__(self, item):
        self.__delitem__(item)

    def __delitem__(self, key):
        super().__delitem__(key)
        del self.__dict__[key]


def cap_words(value):
    """
    Capitalizes the first character of every word in the value.
    Use except_words dict for exceptions.
    """
    if value is None:
        return None
    words = []
    except_words = ['of', 'or', 'in', 'on', 'to', 'the']
    for elem in value.replace('_', ' ').split():
        if elem in except_words:
            words.append(elem)
        else:
            words.append(elem[0].upper() + elem[1:])
    return value and ' '.join(words)


def clean_html_tags(html):
    """
    Simple regex HTML tag cleaner.
    """
    return re.sub(r'<.+?>', '', html)


def construct_full_url(request, rel_url):
    """
    URL constructor based on request and relative URL.
    :param request: request object
    :param rel_url: URL, beginning with slash
    :return:
    """
    protocol = 'https' if request.is_secure() else 'http'
    return '{protocol}://{host}{rel_url}'.format(
        protocol=protocol, host=request.get_host(), rel_url=rel_url)


def export_qs_to_file(request, qs, column_names=None,
                      file_type='xlsx', file_name=None,
                      url_name=None, get_params=None,
                      url_arg=None):
    """
    Export query to file.

    :param request:
    :param qs:
    :param column_names:
    :param file_type:
    :param file_name:
    :param url_name:
    :param get_params:
    :param url_arg:
    :return:
    """

    # columns names - go into file
    # fields - extract from db

    column_names = list(column_names)

    # construct file name if it's not given
    if file_name is None:
        file_name = '{}_list_{}.{}'.format(
            qs.model._meta.model_name,
            datetime.datetime.now().isoformat(),
            file_type
        )

    # split fields into fk, m2m, others
    fields = [f.name for f in qs.model._meta.local_fields
              if f.__class__.__name__ not in ('ManyToOneRel', 'ForeignKey')]
    fields_fk = [f.name for f in qs.model._meta.local_fields
                 if f.__class__.__name__ == 'ForeignKey']
    fields_m2m = [f.name for f in qs.model._meta.many_to_many]

    fields_rtf = [f.name for f in qs.model._meta.local_fields
                  if f.__class__.__name__ == 'RichTextField']

    # if custom column names
    if column_names is not None:
        fields_fk = set(column_names) & set(fields_fk)
        fields_m2m = set(column_names) & set(fields_m2m)
        fields = list(set(column_names) - fields_fk - fields_m2m)
    else:
        column_names = fields + list(fields_fk) + list(fields_m2m)

    if url_name is not None:
        column_names.append('link')

    if 'pk' not in fields:
        fields.append('pk')

    if url_arg:
        fields.append(url_arg)

    # get data from local fields (not fk or m2m)
    data = qs.values(*fields)

    get_params = get_params(request) if callable(get_params) else get_params
    get_params = '?{}'.format(get_params) if get_params else ''

    for item in data:

        # add link to concrete object to each row if needed
        if url_name is not None:
            item['link'] = construct_full_url(
                request,
                reverse(
                    url_name,
                    args=[item[url_arg] if url_arg else item['pk']])) + get_params

        # hit db only if these fields are present
        if fields_fk or fields_m2m:
            obj = qs.model.objects.get(pk=item['pk'])
            # get __str__ for fk
            for fk_field in fields_fk:
                item[fk_field] = str(getattr(obj, fk_field))
            # get list of __str__ for each object in m2m
            for m2m_field in fields_m2m:
                item[m2m_field] = ', '.join([str(i) for i in getattr(obj, m2m_field).all()])
        # clean ReachTextField value from html tags
        for rtf_field in fields_rtf:
            item[rtf_field] = clean_html_tags(item[rtf_field])

    # convert to array
    array_header = list([cap_words(re.sub(r'_+', ' ', i)) for i in column_names])
    array_data = [[row[field_name] for field_name in column_names] for row in data]
    array = [array_header] + array_data

    return excel.make_response_from_array(
        array, file_type, status=200, file_name=file_name,
        sheet_name='book')


def create_standard_urls(model, views, view_types=('list', 'add', 'detail', 'update', 'delete')):
    """
    Create standard urls based on slugified model name
    :param model: actual model
    :param views: views
    :param view_types: list or tuple ('list', 'add', 'detail', 'update', 'delete')
    :return:
    """
    model_slug = slugify(model._meta.verbose_name)
    view_pattern = '%s{}%s' % (model.__name__, 'View')
    urlpatterns = []

    if 'top_list' in view_types:
        urlpatterns += [
            url(r'^{}/list/$'.format('top-' + model_slug),
                getattr(views, 'Top' + view_pattern.format('List')).as_view(),
                name='top-{}-list'.format(model_slug))]
    if 'list' in view_types:
        urlpatterns += [
            url(r'^{}/list/$'.format(model_slug),
                getattr(views, view_pattern.format('List')).as_view(),
                name='{}-list'.format(model_slug))]
    if 'add' in view_types:
        urlpatterns += [
            url(r'^{}/add/$'.format(model_slug),
                getattr(views, view_pattern.format('Create')).as_view(),
                name='{}-add'.format(model_slug))]
    if 'detail' in view_types:
        urlpatterns += [
            url(r'^{}/(?P<pk>\d+)/detail/$'.format(model_slug),
                getattr(views, view_pattern.format('Detail')).as_view(),
                name='{}-detail'.format(model_slug))]
    if 'update' in view_types:
        urlpatterns += [
            url(r'^{}/(?P<pk>\d+)/update/$'.format(model_slug),
                getattr(views, view_pattern.format('Update')).as_view(),
                name='{}-update'.format(model_slug))]
    if 'delete' in view_types:
        urlpatterns += [
            url(r'^{}/(?P<pk>\d+)/delete/$'.format(model_slug),
                getattr(views, view_pattern.format('Delete')).as_view(),
                name='{}-delete'.format(model_slug))]
    return urlpatterns


def fast_uuid():
    return uuid.UUID(int=random.getrandbits(128), version=4)


def get_api_module(app_name):
    module_path_str = 'apps.{app_name}.api.{api_version}'.format(
        app_name=app_name,
        api_version=settings.REST_FRAMEWORK['DEFAULT_VERSION']
    )
    return importlib.import_module(module_path_str)


def download_xls(data: pd.DataFrame, file_name='output', sheet_name='doc'):
    if isinstance(data, list):
        data = pd.DataFrame(data)
    buffer = io.BytesIO()
    writer = pd.ExcelWriter(buffer, engine='xlsxwriter')
    data.to_excel(writer, index=False, sheet_name=sheet_name, encoding='utf-8')
    writer.save()
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="{}.{}"'.format(file_name, 'xlsx')
    response.write(buffer.getvalue())
    return response


def download_csv(data: pd.DataFrame, file_name='output'):
    buffer = io.StringIO()
    data.to_csv(buffer, index=False, encoding='utf-8')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{}.{}"'.format(file_name, 'csv')
    response.write(buffer.getvalue())
    return response


def download_pdf(data: pd.DataFrame, file_name='output'):
    data_html = data.to_html(index=False)
    try:
        data_pdf = pdf.from_string(data_html, False)
    except OSError:
        env = Environment(loader=FileSystemLoader(settings.PROJECT_DIR('templates')))
        template = env.get_template('pdf_export.html')
        template_vars = {"title": file_name.capitalize(),
                         "table": data_html}
        data_pdf = HTML(string=template.render(template_vars)).write_pdf()
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="{}.{}"'.format(file_name, 'pdf')
    response.write(data_pdf)
    return response


def download(data: [list, pd.DataFrame], fmt='csv', file_name='output'):
    if not isinstance(data, pd.DataFrame):
        data = pd.DataFrame(data)
    data[data.select_dtypes(['object', 'datetime64[ns, UTC]']).columns] = data.select_dtypes(['object', 'datetime64[ns, UTC]']).apply(lambda x: x.astype(str))
    data.fillna('', inplace=True)
    if fmt == 'xlsx':
        return download_xls(data, file_name=file_name)
    if fmt == 'pdf':
        return download_pdf(data, file_name=file_name)
    else:
        return download_csv(data, file_name=file_name)


def get_test_user():
    from allauth.account.models import EmailAddress
    test_user, created = User.objects.update_or_create(
        username='test_user',
        defaults=dict(
            first_name='Test',
            last_name='User',
            name='Test User',
            email='test@user.com',
            role=Role.objects.filter(is_manager=True).first(),
            is_active=True))
    if created:
        test_user.set_password('test_user')
        test_user.save()
        EmailAddress.objects.create(
            user=test_user,
            email=test_user.email,
            verified=True,
            primary=True)

    return test_user


def format_number(num):
    """
    Add thousand separator to a number
    """
    return numberformat.format(num,
                               grouping=3,
                               decimal_sep='.',
                               thousand_sep=',',
                               force_grouping=True)


class Serializable(dict):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # hack to fix _json.so make_encoder serialize properly
        self.__setitem__('dummy', 1)

    def _myattrs(self):
        return [
            (x, self._repr(getattr(self, x)))
            for x in self.__dir__()
            if x not in Serializable().__dir__()
        ]

    def _repr(self, value):
        if isinstance(value, (str, int, float, list, tuple, dict)):
            return value
        else:
            return repr(value)

    def __repr__(self):
        return '<%s.%s object at %s>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            hex(id(self))
        )

    def keys(self):
        return iter([x[0] for x in self._myattrs()])

    def values(self):
        return iter([x[1] for x in self._myattrs()])

    def items(self):
        return iter(self._myattrs())
