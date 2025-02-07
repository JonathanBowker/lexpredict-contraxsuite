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

from lexnlp.extract.en import dict_entities
from lexnlp.nlp.en.tokens import get_stems

from apps.common.db_cache.db_cache import DbCache
from apps.extract.models import GeoEntity, GeoAlias, Court, Term

__author__ = "ContraxSuite, LLC; LexPredict, LLC"
__copyright__ = "Copyright 2015-2019, ContraxSuite, LLC"
__license__ = "https://github.com/LexPredict/lexpredict-contraxsuite/blob/1.2.3/LICENSE"
__version__ = "1.2.3"
__maintainer__ = "LexPredict, LLC"
__email__ = "support@contraxsuite.com"


CACHE_KEY_GEO_CONFIG = 'geo_config'
CACHE_KEY_COURT_CONFIG = 'court_config'
CACHE_KEY_TERM_STEMS = 'term_stems'


def cache_geo_config():
    geo_config = {}
    for name, pk, priority in GeoEntity.objects.values_list('name', 'pk', 'priority'):
        entity = dict_entities.entity_config(pk, name, priority or 0, name_is_alias=True)
        geo_config[pk] = entity
    for alias_id, alias_text, alias_type, entity_id, alias_lang \
            in GeoAlias.objects.values_list('pk', 'alias', 'type', 'entity', 'locale'):
        entity = geo_config[entity_id]
        if entity:
            is_abbrev = alias_type.startswith('iso') or alias_type.startswith('abbrev')
            dict_entities.add_aliases_to_entity(entity,
                                                aliases_csv=alias_text,
                                                language=alias_lang,
                                                is_abbreviation=is_abbrev,
                                                alias_id=alias_id)
    res = list(geo_config.values())
    DbCache.put_to_db(CACHE_KEY_GEO_CONFIG, res)


def get_geo_config():
    return DbCache.get(CACHE_KEY_GEO_CONFIG)


def cache_court_config():
    res = [dict_entities.entity_config(
        entity_id=i.id,
        name=i.name,
        priority=0,
        aliases=i.alias.split(';') if i.alias else []
    ) for i in Court.objects.all()]
    DbCache.put_to_db(CACHE_KEY_COURT_CONFIG, res)


def get_court_config():
    return DbCache.get(CACHE_KEY_COURT_CONFIG)


def cache_term_stems():
    term_stems = {}
    for t, pk in Term.objects.values_list('term', 'pk'):
        stemmed_term = ' %s ' % ' '.join(get_stems(t))
        stemmed_item = term_stems.get(stemmed_term, [])
        stemmed_item.append([t, pk])
        term_stems[stemmed_term] = stemmed_item
    for item in term_stems:
        term_stems[item] = dict(values=term_stems[item],
                                length=len(term_stems[item]))
    DbCache.put_to_db(CACHE_KEY_TERM_STEMS, term_stems)


def get_term_config():
    return DbCache.get(CACHE_KEY_TERM_STEMS)
