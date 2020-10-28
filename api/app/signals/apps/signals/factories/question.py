from factory import DjangoModelFactory
from factory.fuzzy import FuzzyChoice, FuzzyText

from signals.apps.signals.models import Question


class QuestionFactory(DjangoModelFactory):
    key = FuzzyText(length=3)
    field_type = FuzzyChoice(choices=list(dict(Question.FIELD_TYPE_CHOICES).keys()))
    meta = '{ "dummy" : "test" }'
    required = FuzzyChoice(choices=[True, False])

    class Meta:
        model = Question
