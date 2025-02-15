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

# Django imports
from django.contrib import admin

from rest_framework_tracking.admin import APIRequestLogAdmin

# Project imports
from apps.common.models import AppVar, ReviewStatusGroup, ReviewStatus, Action,\
    CustomAPIRequestLog, APIRequestLog

__author__ = "ContraxSuite, LLC; LexPredict, LLC"
__copyright__ = "Copyright 2015-2019, ContraxSuite, LLC"
__license__ = "https://github.com/LexPredict/lexpredict-contraxsuite/blob/1.2.3/LICENSE"
__version__ = "1.2.3"
__maintainer__ = "LexPredict, LLC"
__email__ = "support@contraxsuite.com"


class AppVarAdmin(admin.ModelAdmin):
    list_display = ('name', 'value', 'user', 'description', 'date')
    search_fields = ('name', 'description')


class ReviewStatusGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'order', 'is_active')
    search_fields = ('name', 'code')


class ReviewStatusAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'order', 'group', 'is_active')
    search_fields = ('name', 'code')


class ActionAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'object', 'date')
    search_fields = ('name', 'user__username')


admin.site.unregister(APIRequestLog)

admin.site.register(CustomAPIRequestLog, APIRequestLogAdmin)
admin.site.register(AppVar, AppVarAdmin)
admin.site.register(ReviewStatusGroup, ReviewStatusGroupAdmin)
admin.site.register(ReviewStatus, ReviewStatusAdmin)
admin.site.register(Action, ActionAdmin)
