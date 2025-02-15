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

import math

import fuzzywuzzy.fuzz
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from apps.analyze.models import (
    DocumentSimilarity, TextUnitSimilarity, PartySimilarity as PartySimilarityModel)
from apps.celery import app
from apps.document.fields_processing.document_vectorizers import document_feature_vector_pipeline
from apps.document.models import DocumentField, DocumentFieldValue, TextUnit, Document
from apps.extract.models import Party
from apps.rawdb.field_value_tables import FIELD_CODE_DOC_ID
from apps.rawdb.repository.raw_db_repository import RawDbRepository
from apps.similarity.models import DocumentSimilarityConfig, DST_FIELD_SIMILARITY_CONFIG_ATTR
from apps.task.tasks import BaseTask, remove_punctuation_map

__author__ = "ContraxSuite, LLC; LexPredict, LLC"
__copyright__ = "Copyright 2015-2019, ContraxSuite, LLC"
__license__ = "https://github.com/LexPredict/lexpredict-contraxsuite/blob/1.2.3/LICENSE"
__version__ = "1.2.3"
__maintainer__ = "LexPredict, LLC"
__email__ = "support@contraxsuite.com"


# TODO: Configuration-based and language-based stemmer.

# Create global stemmer
stemmer = nltk.stem.porter.PorterStemmer()


def normalize(text):
    """
    Simple text normalizer returning stemmed, lowercased tokens.
    :param text:
    :return:
    """
    return stem_tokens(nltk.word_tokenize(text.lower().translate(remove_punctuation_map)))


def stem_tokens(tokens):
    """
    Simple token stemmer.
    :param tokens:
    :return:
    """
    res = []
    for item in tokens:
        try:
            res.append(stemmer.stem(item))
        except IndexError:
            pass
    return res


class PartySimilarity(BaseTask):
    """
    Task for the identification of similar party names.
    """
    name = 'Party Similarity'

    def process(self, **kwargs):
        """
        Task process method.
        :param kwargs: dict, form data
        """
        parties = Party.objects.values_list('pk', 'name')
        self.set_push_steps(len(parties) + 1)

        # 1. Delete if requested
        if kwargs['delete']:
            PartySimilarityModel.objects.all().delete()

        # 2. Select scorer
        scorer = getattr(fuzzywuzzy.fuzz, kwargs['similarity_type'])

        # 3. Iterate through all pairs
        similar_results = []
        for party_a_pk, party_a_name in parties:
            for party_b_pk, party_b_name in parties:
                if party_a_pk == party_b_pk:
                    continue

                # Calculate similarity
                if not kwargs['case_sensitive']:
                    party_a_name = party_a_name.upper()
                    party_b_name = party_b_name.upper()

                score = scorer(party_a_name, party_b_name)
                if score >= kwargs['similarity_threshold']:
                    similar_results.append(
                        PartySimilarityModel(
                            party_a_id=party_a_pk,
                            party_b_id=party_b_pk,
                            similarity=score))
            self.push()

        # 4. Bulk create similarity objects
        PartySimilarityModel.objects.bulk_create(similar_results)
        self.push()


class Similarity(BaseTask):
    """
    Find Similar Documents, Text Units
    """
    name = 'Similarity'
    verbose = True
    n_features = 100
    self_name_len = 3
    step = 2000

    def process(self, **kwargs):
        """

        :param kwargs:
        :return:
        """

        search_similar_documents = kwargs['search_similar_documents']
        search_similar_text_units = kwargs['search_similar_text_units']
        similarity_threshold = kwargs['similarity_threshold']
        self.log_info('Min similarity: %d' % similarity_threshold)

        # get text units with min length 100 signs
        text_units = TextUnit.objects.filter(unit_type='paragraph',
                                             text__regex=r'.{100}.*')
        len_tu_set = text_units.count()

        push_steps = 0
        if search_similar_documents:
            push_steps += 4
        if search_similar_text_units:
            push_steps += math.ceil(len_tu_set / self.step) ** 2 + 3
        self.set_push_steps(push_steps)

        # similar Documents
        if search_similar_documents:

            # step #1 - delete
            if kwargs['delete']:
                DocumentSimilarity.objects.all().delete()
            self.push()

            # step #2 - prepare data
            texts_set = ['\n'.join(d.textunit_set.values_list('text', flat=True))
                         for d in Document.objects.all()]
            self.push()

            # step #3
            vectorizer = TfidfVectorizer(max_df=0.5, max_features=self.n_features,
                                         min_df=2, stop_words='english',
                                         use_idf=kwargs['use_idf'])
            X = vectorizer.fit_transform(texts_set)
            self.push()

            # step #4
            similarity_matrix = cosine_similarity(X) * 100
            pks = Document.objects.values_list('pk', flat=True)
            for x, document_a in enumerate(pks):
                # use it to search for unique a<>b relations
                # for y, document_b in enumerate(Document.objects.all()[x + 1:], start=x + 1):
                for y, document_b in enumerate(pks):
                    if document_a == document_b:
                        continue
                    similarity = similarity_matrix[x, y]
                    if similarity < similarity_threshold:
                        continue
                    DocumentSimilarity.objects.create(
                        document_a_id=document_a,
                        document_b_id=document_b,
                        similarity=similarity)
            self.push()

        # similar Text Units
        if search_similar_text_units:

            # step #1 - delete
            if kwargs['delete']:
                TextUnitSimilarity.objects.all().delete()
            self.push()

            # step #2 - prepare data
            texts_set, pks = zip(*text_units.values_list('text', 'pk'))
            self.push()

            # step #3
            vectorizer = TfidfVectorizer(tokenizer=normalize,
                                         max_df=0.5, max_features=self.n_features,
                                         min_df=2, stop_words='english',
                                         use_idf=kwargs['use_idf'])
            X = vectorizer.fit_transform(texts_set)
            self.push()

            # step #4
            for i in range(0, len_tu_set, self.step):
                for j in range(0, len_tu_set, self.step):
                    similarity_matrix = cosine_similarity(
                        X[i:min([i + self.step, len_tu_set])],
                        X[j:min([j + self.step, len_tu_set])]) * 100
                    for g in range(similarity_matrix.shape[0]):
                        tu_sim = [
                            TextUnitSimilarity(
                                text_unit_a_id=pks[i + g],
                                text_unit_b_id=pks[j + h],
                                similarity=similarity_matrix[g, h])
                            for h in range(similarity_matrix.shape[1])
                            if i + g != j + h and similarity_matrix[g, h] >= similarity_threshold]
                        TextUnitSimilarity.objects.bulk_create(tu_sim)
                    self.push()


class PreconfiguredDocumentSimilaritySearch(BaseTask):
    name = 'PreconfiguredDocumentSimilaritySearch'
    verbose = True
    n_features = 100
    self_name_len = 3
    step = 2000

    def process(self, **kwargs):
        dst_field = kwargs['field']
        dst_field = DocumentField.objects.filter(pk=dst_field['pk']) \
            .prefetch_related('depends_on_fields') \
            .select_related(DST_FIELD_SIMILARITY_CONFIG_ATTR) \
            .first()  # type: DocumentField

        if not dst_field:
            raise RuntimeError('Document field not found: {0}'.format(kwargs['field']))

        config = getattr(dst_field, DST_FIELD_SIMILARITY_CONFIG_ATTR)  # type: DocumentSimilarityConfig

        config.self_validate()

        similarity_threshold = config.similarity_threshold
        feature_vector_fields = dst_field.depends_on_fields.all()
        feature_vector_field_codes = {f.code for f in feature_vector_fields}.union({FIELD_CODE_DOC_ID})

        self.log_info('{field}: Min similarity: {threshold}'
                      .format(field=dst_field.code, threshold=similarity_threshold))

        rawdb = RawDbRepository()
        field_values_list = list(rawdb.get_field_values(document_type=dst_field.document_type,
                                                        field_codes=feature_vector_field_codes))

        total_docs = len(field_values_list)

        self.set_push_steps(int(5 + total_docs / 100))

        self.push()
        self.log_info(
            '{field}: Building feature vectors for {n} documents'.format(field=dst_field.code, n=total_docs))

        vectorizer = document_feature_vector_pipeline(feature_vector_fields, use_field_codes=True)
        feature_vectors = vectorizer.fit_transform(field_values_list)

        self.push()
        self.log_info('{field}: Finding similar documents (similarity >= {threshold})'
                      .format(field=dst_field.code, threshold=similarity_threshold))

        dfvs = list()
        for x, doc_a_field_values in enumerate(field_values_list):
            doc_a_pk = doc_a_field_values[FIELD_CODE_DOC_ID]
            similarities = cosine_similarity(feature_vectors[x], feature_vectors)
            for y, doc_b_field_values in enumerate(field_values_list):
                doc_b_pk = doc_b_field_values[FIELD_CODE_DOC_ID]
                if doc_a_pk == doc_b_pk:
                    continue
                similarity = similarities[0, y]
                if similarity < similarity_threshold:
                    continue
                dfvs.append(DocumentFieldValue(document_id=doc_a_pk, value=doc_b_pk, field_id=dst_field.pk))
                dfvs.append(DocumentFieldValue(document_id=doc_b_pk, value=doc_a_pk, field_id=dst_field.pk))
            if x % 100 == 0:
                self.log_info('{field}: Checked for similarity {x} documents of {n}'
                              .format(field=dst_field.code, x=x + 1, n=total_docs))
                self.push()

        self.push()
        self.log_info('{field}: Found {n} similar documents. Storing links into the document fields.'
                      .format(field=dst_field.code, n=len(dfvs)))

        del_doc_batch_size = 100
        for i in range(0, len(field_values_list), del_doc_batch_size):
            DocumentFieldValue.objects \
                .filter(field_id=dst_field.pk) \
                .filter(document_id__in={field_values[FIELD_CODE_DOC_ID] for field_values
                                         in field_values_list[i: i + del_doc_batch_size]}) \
                .delete()
        DocumentFieldValue.objects.bulk_create(dfvs)
        self.push()


app.register_task(PreconfiguredDocumentSimilaritySearch())
app.register_task(Similarity())
app.register_task(PartySimilarity())
