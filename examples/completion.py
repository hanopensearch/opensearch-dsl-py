"""
Example ``Document`` with completion suggester.

In the ``Person`` class we index the person's name to allow auto completing in
any order ("first last", "middle last first", ...). For the weight we use a
value from the ``popularity`` field which is a long.

To make the suggestions work in different languages we added a custom analyzer
that does ascii folding.
"""
from __future__ import print_function

from itertools import permutations

from elasticsearch_dsl import connections, Document, Completion, Text, Long, \
        Keyword, analyzer, token_filter

# custom analyzer for names
ascii_fold = analyzer(
    'ascii_fold',
    # we don't want to split O'Brian or Toulouse-Lautrec
    tokenizer='whitespace',
    filter=[
        'lowercase',
        token_filter('ascii_fold', 'asciifolding')
    ]
)


class Person(Document):
    name = Text(fields={'keyword': Keyword()})
    popularity = Long()

    # copletion field with a custom analyzer
    suggest = Completion(analyzer=ascii_fold)

    def clean(self):
        """
        Automatically construct the suggestion input and weight by taking all
        possible permutation of Person's name as ``input`` and taking their
        popularity as ``weight``.
        """
        self.suggest = {
            'input': [' '.join(p) for p in permutations(self.name.split())],
            'weight': self.popularity
        }

    class Index:
        name = 'test-suggest'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0
        }


if __name__ == '__main__':
    # initiate the default connection to elasticsearch
    connections.create_connection()

    # create the empty index
    Person.init()

    # index some sample data
    for id, (name, popularity) in enumerate([
                ('Henri de Toulouse-Lautrec', 42),
                ('Jára Cimrman', 124),
            ]):
        Person(_id=id, name=name, popularity=popularity).save()

    # refresh index manually to make changes live
    Person._index.refresh()

    # run some suggestions
    for text in ('já', 'Jara Cimr', 'tou', 'de hen'):
        s = Person.search()
        s = s.suggest('auto_complete', text, completion={'field': 'suggest'})
        response = s.execute()

        # print out all the options we got
        for option in response.suggest.auto_complete[0].options:
            print('%10s: %25s (%d)' % (text, option._source.name, option._score))