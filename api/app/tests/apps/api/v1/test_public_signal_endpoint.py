import json
import os
from unittest import skip

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from signals.apps.signals import workflow
from signals.apps.signals.models import Attachment, Priority, Signal, Type
from tests.apps.signals.attachment_helpers import small_gif
from tests.apps.signals.factories import CategoryFactory, SignalFactory
from tests.test import SignalsBaseApiTestCase

THIS_DIR = os.path.dirname(__file__)
SIGNALS_TEST_DIR = os.path.join(os.path.split(THIS_DIR)[0], '..', 'signals')


class TestPublicSignalViewSet(SignalsBaseApiTestCase):
    list_endpoint = "/signals/v1/public/signals/"
    detail_endpoint = list_endpoint + "{uuid}"
    attachment_endpoint = detail_endpoint + "/attachments"

    fixture_file = os.path.join(THIS_DIR, 'request_data', 'create_initial.json')

    def setUp(self):
        with open(self.fixture_file, 'r') as f:
            self.create_initial_data = json.load(f)

        self.subcategory = CategoryFactory.create()

        self.link_test_cat_sub = '/signals/v1/public/terms/categories/{}/sub_categories/{}'.format(
            self.subcategory.parent.slug, self.subcategory.slug
        )

        self.create_initial_data['category'] = {'sub_category': self.link_test_cat_sub}

        self.retrieve_schema = self.load_json_schema(
            os.path.join(
                THIS_DIR,
                'json_schema',
                'get_signals_v1_public_signals_{uuid}.json'
            )
        )
        self.create_schema = self.load_json_schema(
            os.path.join(
                THIS_DIR,
                'json_schema',
                'post_signals_v1_public_signals.json'
            )
        )
        self.create_attachment_schema = self.load_json_schema(
            os.path.join(
                THIS_DIR,
                'json_schema',
                'post_signals_v1_public_signals_attachment.json'
            )
        )

    def test_create(self):
        response = self.client.post(self.list_endpoint, self.create_initial_data, format='json')

        self.assertEqual(201, response.status_code)
        self.assertJsonSchema(self.create_schema, response.json())
        self.assertEqual(1, Signal.objects.count())

        signal = Signal.objects.last()
        self.assertEqual(workflow.GEMELD, signal.status.state)
        self.assertEqual(self.subcategory, signal.category_assignment.category)
        self.assertEqual("melder@example.com", signal.reporter.email)
        self.assertEqual("Amstel 1 1011PN Amsterdam", signal.location.address_text)
        self.assertEqual("Luidruchtige vergadering", signal.text)
        self.assertEqual("extra: heel luidruchtig debat", signal.text_extra)
        self.assertEqual('SIG', signal.type_assignment.name)

    def test_create_with_status(self):
        """ Tests that an error is returned when we try to set the status """

        initial_data = self.create_initial_data.copy()
        initial_data["status"] = {
            "state": workflow.BEHANDELING,
            "text": "Invalid stuff happening here"
        }

        response = self.client.post(self.list_endpoint, initial_data, format='json')

        self.assertEqual(400, response.status_code)
        self.assertEqual(0, Signal.objects.count())

    def test_create_with_priority(self):
        # must not be able to set priority
        initial_data = self.create_initial_data.copy()
        initial_data['priorty'] = {
            'priority': Priority.PRIORITY_HIGH
        }
        response = self.client.post(self.list_endpoint, initial_data, format='json')
        response_json = response.json()

        self.assertEqual(201, response.status_code)
        self.assertEqual(1, Signal.objects.count())

        pk = response_json['id']
        signal = Signal.objects.get(pk=pk)
        self.assertEqual(signal.priority.priority, Priority.PRIORITY_NORMAL)

    def test_create_with_type(self):
        # must not be able to set type
        initial_data = self.create_initial_data.copy()
        initial_data['type'] = {
            'code': Type.COMPLAINT
        }
        response = self.client.post(self.list_endpoint, initial_data, format='json')
        response_json = response.json()

        self.assertEqual(201, response.status_code)
        self.assertEqual(1, Signal.objects.count())

        pk = response_json['id']
        signal = Signal.objects.get(pk=pk)
        self.assertEqual(signal.type_assignment.name, Type.SIGNAL)

    def test_create_with_source(self):
        # must not be able to set the source
        bad_source = 'DIT MAG NIET'
        initial_data = self.create_initial_data.copy()
        initial_data['source'] = bad_source

        response = self.client.post(self.list_endpoint, initial_data, format='json')

        self.assertEqual(400, response.status_code)
        self.assertEqual(response.json()['source'], ['Invalid source given for anonymous user'])
        self.assertEqual(0, Signal.objects.count())

    def test_get_by_uuid(self):
        signal = SignalFactory.create()
        uuid = signal.signal_id

        response = self.client.get(self.detail_endpoint.format(uuid=uuid), format='json')

        self.assertEqual(200, response.status_code)
        self.assertJsonSchema(self.retrieve_schema, response.json())

    def test_get_by_uuid_access_status(self):
        # SIA must not publicly expose what step in the resolution process a certain
        # Signal/melding is
        signal = SignalFactory.create(status__state=workflow.GEMELD)
        uuid = signal.signal_id

        response = self.client.get(self.detail_endpoint.format(uuid=uuid), format='json')
        response_json = response.json()

        self.assertEqual(200, response.status_code)
        self.assertJsonSchema(self.retrieve_schema, response_json)
        self.assertEqual(response_json['status']['state'], 'OPEN')

        signal = SignalFactory.create(status__state=workflow.AFGEHANDELD)
        uuid = signal.signal_id

        response = self.client.get(self.detail_endpoint.format(uuid=uuid), format='json')
        response_json = response.json()

        self.assertEqual(200, response.status_code)
        self.assertJsonSchema(self.retrieve_schema, response_json)
        self.assertEqual(response_json['status']['state'], 'CLOSED')

    def test_get_by_uuid__display_is_clean(self):
        # SIA must not publicly expose what step in the resolution process a certain
        # Signal/melding is via the _display string.
        signal = SignalFactory.create()
        uuid = signal.signal_id

        response = self.client.get(self.detail_endpoint.format(uuid=uuid), format='json')
        response_json = response.json()

        self.assertEqual(200, response.status_code)
        self.assertJsonSchema(self.retrieve_schema, response_json)
        # For backwards compatibility the _display string is not changed, we use the
        # fact that it is derived from the __str__ representation, to do this check.
        self.assertNotEqual(response_json['_display'], str(signal))

    def test_get_by_uuid_cannot_access_properties(self):
        # SIA must not publicly expose operational date, expire_date and attachments
        signal = SignalFactory.create()
        uuid = signal.signal_id

        response = self.client.get(self.detail_endpoint.format(uuid=uuid), format='json')
        response_json = response.json()

        self.assertEqual(200, response.status_code)
        self.assertJsonSchema(self.retrieve_schema, response_json)
        self.assertNotIn('operational_date', response_json)
        self.assertNotIn('expire_date', response_json)
        self.assertNotIn('attachments', response_json)

    def test_add_attachment_imagetype(self):
        signal = SignalFactory.create()
        uuid = signal.signal_id

        data = {"file": SimpleUploadedFile('image.gif', small_gif, content_type='image/gif')}

        response = self.client.post(self.attachment_endpoint.format(uuid=uuid), data)

        self.assertEqual(201, response.status_code)
        self.assertJsonSchema(self.create_attachment_schema, response.json())

        attachment = Attachment.objects.last()
        self.assertEqual("image/gif", attachment.mimetype)
        self.assertIsInstance(attachment.image_crop.url, str)
        self.assertIsNone(attachment.created_by)

    def test_add_attachment_nonimagetype(self):
        signal = SignalFactory.create()
        uuid = signal.signal_id

        doc_upload = os.path.join(SIGNALS_TEST_DIR, 'sia-ontwerp-testfile.doc')
        with open(doc_upload, encoding='latin-1') as f:
            data = {"file": f}

            response = self.client.post(self.attachment_endpoint.format(uuid=uuid), data)

        self.assertEqual(201, response.status_code)
        self.assertJsonSchema(self.create_attachment_schema, response.json())

        attachment = Attachment.objects.last()
        self.assertEqual("application/msword", attachment.mimetype)

    def test_cannot_access_attachments(self):
        # SIA must not publicly expose attachments
        signal = SignalFactory.create()
        uuid = signal.signal_id

        response = self.client.get(self.attachment_endpoint.format(uuid=uuid))
        self.assertEqual(response.status_code, 405)

    def test_create_with_invalid_source_user(self):
        data = self.create_initial_data
        data['source'] = 'invalid-source'
        response = self.client.post(self.list_endpoint, data, format='json')

        self.assertEqual(400, response.status_code)
        self.assertEqual(response.json()['source'][0], 'Invalid source given for anonymous user')

    @override_settings(FEATURE_FLAGS={'API_VALIDATE_EXTRA_PROPERTIES': True})
    def test_validate_extra_properties_enabled(self):
        initial_data = self.create_initial_data.copy()
        initial_data['extra_properties'] = [{
            'id': 'test_id',
            'label': 'test_label',
            'answer': {
                'id': 'test_answer',
                'value': 'test_value'
            },
            'category_url': self.link_test_cat_sub
        }, {
            'id': 'test_id',
            'label': 'test_label',
            'answer': 'test_answer',
            'category_url': self.link_test_cat_sub
        }, {
            'id': 'test_id',
            'label': 'test_label',
            'answer': ['a', 'b', 'c'],
            'category_url': self.link_test_cat_sub
        }]

        response = self.client.post(self.list_endpoint, initial_data, format='json')

        self.assertEqual(201, response.status_code)
        self.assertEqual(1, Signal.objects.count())

    @override_settings(FEATURE_FLAGS={'API_VALIDATE_EXTRA_PROPERTIES': True})
    def test_validate_extra_properties_enabled_invalid_data(self):
        initial_data = self.create_initial_data.copy()
        initial_data['extra_properties'] = {'old_style': 'extra_properties'}

        response = self.client.post(self.list_endpoint, initial_data, format='json')
        data = response.json()

        self.assertEqual(400, response.status_code)
        self.assertIn('extra_properties', data)
        self.assertEqual(data['extra_properties'][0], 'Invalid input.')
        self.assertEqual(0, Signal.objects.count())

    @override_settings(FEATURE_FLAGS={'API_VALIDATE_EXTRA_PROPERTIES': False})
    def test_validate_extra_properties_disabled(self):
        initial_data = self.create_initial_data.copy()
        initial_data['extra_properties'] = {'old_style': 'extra_properties'}

        response = self.client.post(self.list_endpoint, initial_data, format='json')

        self.assertEqual(201, response.status_code)
        self.assertEqual(1, Signal.objects.count())

    @skip('public serialization no longer contains extra_properties field')
    @override_settings(FEATURE_FLAGS={'API_FILTER_EXTRA_PROPERTIES': True})
    def test_filtered_extra_properties(self):
        initial_data = self.create_initial_data.copy()
        initial_data['extra_properties'] = [{
            'id': 'test_id',
            'label': 'test_label',
            'answer': {
                'id': 'test_answer',
                'value': 'test_value'
            },
            'category_url': self.link_test_cat_sub
        }, {
            'id': 'test_id',
            'label': 'test_label',
            'answer': 'test_answer',
            'category_url': self.link_test_cat_sub
        }, {
            'id': 'test_id',
            'label': 'test_label',
            'answer': ['a', 'b', 'c'],
            'category_url': 'this/is/a/different/category/we/do/not/want/this/in/the/response'
        }]

        response = self.client.post(self.list_endpoint, initial_data, format='json')

        self.assertEqual(201, response.status_code)
        self.assertEqual(1, Signal.objects.count())

        data = response.json()
        self.assertEqual(len(data['extra_properties']), 2)
        self.assertEqual(data['extra_properties'][0]['category_url'], self.link_test_cat_sub)
        self.assertEqual(data['extra_properties'][1]['category_url'], self.link_test_cat_sub)

    @skip('public serialization no longer contains extra_properties field')
    @override_settings(FEATURE_FLAGS={'API_FILTER_EXTRA_PROPERTIES': False})
    def test_no_filtered_extra_properties(self):
        initial_data = self.create_initial_data.copy()
        initial_data['extra_properties'] = [{
            'id': 'test_id',
            'label': 'test_label',
            'answer': {
                'id': 'test_answer',
                'value': 'test_value'
            },
            'category_url': self.link_test_cat_sub
        }, {
            'id': 'test_id',
            'label': 'test_label',
            'answer': 'test_answer',
            'category_url': self.link_test_cat_sub
        }, {
            'id': 'test_id',
            'label': 'test_label',
            'answer': ['a', 'b', 'c'],
            'category_url': 'this/is/a/different/category/we/do/not/want/this/in/the/response'
        }]

        response = self.client.post(self.list_endpoint, initial_data, format='json')

        self.assertEqual(201, response.status_code)
        self.assertEqual(1, Signal.objects.count())

        data = response.json()
        self.assertEqual(len(data['extra_properties']), 3)
        self.assertEqual(data['extra_properties'][0]['category_url'], self.link_test_cat_sub)
        self.assertEqual(data['extra_properties'][1]['category_url'], self.link_test_cat_sub)
        self.assertEqual(data['extra_properties'][2]['category_url'], 'this/is/a/different/category/we/do/not/want/this/in/the/response') # noqa

    def test_signal_type_cannot_be_posted(self):
        initial_data = self.create_initial_data.copy()

        initial_data['type'] = {'code', 'REQ'}
        response = self.client.post(self.list_endpoint, initial_data, format='json')
        self.assertEqual(201, response.status_code)

        # Check that both in the API and in the database the new Signal is of
        # type SIG (the default, even though we tried to set something else).
        signal = Signal.objects.last()
        self.assertEqual(signal.type_assignment.name, 'SIG')
