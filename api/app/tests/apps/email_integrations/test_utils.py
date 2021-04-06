# SPDX-License-Identifier: MPL-2.0
# Copyright (C) 2021 Gemeente Amsterdam
import re

from django.conf import settings
from django.test import TestCase
from faker import Faker

from signals.apps.email_integrations.factories import EmailTemplateFactory
from signals.apps.email_integrations.models import EmailTemplate
from signals.apps.email_integrations.utils import (
    URL_PATTERN,
    make_email_context,
    validate_email_template,
    validate_template
)
from signals.apps.signals.factories import SignalFactory


class TestUtils(TestCase):
    def test_regex(self):
        """
        Check if a URL matches the URL_PATTERN
        Check if the URL is replaced by ''
        Check if the URL is replaced by '' if we put it in a random text

        We test with a couple of examples we can think of and a couple of examples created by the Faker
        """
        test_schemas = ['http://', 'https://', 'ftp://', 'sftp://', 'file://', 'chrome://', 'chrome-extension://',
                        'dns://', 'git://', 'irc://', 'ldap://', 'smb://', 'z39.50r://', 'z39.50s://', '', ]

        test_uris = [
            'test-domain.com',
            'www.test-domain.com/',
            'test-domain.com?query=param',
            'test-domain.com/?query=param',
            'www.test-domain.com/with/path?query=param',
            'test-domain.com/with/path/?query=param',
            'test-domain.com?query=param&extra=param',
            'test-domain.com/?query=param&extra=param',
            'www.test-domain.com/with/path?query=param&extra=param',
            'test-domain.com/with/path/?query=param&extra=param',
            'test-domain.com:8080',
            'www.test-domain.com:8080/',
            'user:password@test-domain.com',
            'user:password@test-domain.com/',
            'user:password@test-domain.com:8080',
            'user:password@www.test-domain.com:8080/',
            'test-domain.com:8080?query=param',
            'test-domain.com:8080/?query=param&extra=param',
            'user:password@test-domain.com?query=param',
            'user:password@test-domain.com/?query=param&extra=param',
            'user:password@test-domain.com:8080?query=param',
            'user:password@test-domain.com:8080/?query=param&extra=param',
            'test-domain.co.uk',
            'www.test-domain.co.uk/',
            'úêï.google',
            'www.úêï.google/',
            'strangetld.lol',
            'strangetld.fun',
            'strangetld.wow',
            'strangetld.unicorn',
            'www.example.com/just/a/path/',
            'test.com',
        ]

        fake = Faker()
        fake_text = fake.text()
        position_to_insert = fake_text.find('.')

        for schema in test_schemas:
            for uri in test_uris:
                test_url = f'{schema}{uri}'
                self.assertRegex(test_url, URL_PATTERN)
                self.assertEqual(0, len(re.sub(URL_PATTERN, '', test_url)))

                fake_text_url = f'{fake_text[:position_to_insert+1]} {test_url} {fake_text[position_to_insert+2:]}'
                self.assertRegex(fake_text_url, URL_PATTERN)
                self.assertNotIn(test_url, re.sub(URL_PATTERN, '', fake_text_url))
                self.assertNotEqual(fake_text_url, re.sub(URL_PATTERN, '', fake_text_url))

        # test some randomly generated URL's/URI's
        for _ in range(25):
            fake_url = fake.url()
            self.assertRegex(fake_url, URL_PATTERN)
            self.assertEqual(0, len(re.sub(URL_PATTERN, '', fake_url)))

            fake_text_url = f'{fake_text[:position_to_insert+1]} {fake_url} {fake_text[position_to_insert+2:]}'
            self.assertRegex(fake_text_url, URL_PATTERN)
            self.assertNotIn(fake_url, re.sub(URL_PATTERN, '', fake_text_url))
            self.assertNotEqual(fake_text_url, re.sub(URL_PATTERN, '', fake_text_url))

            fake_uri = fake.uri()
            self.assertRegex(fake_uri, URL_PATTERN)
            self.assertEqual(0, len(re.sub(URL_PATTERN, '', fake_uri)))

            fake_text_uri = f'{fake_text[:position_to_insert+1]} {fake_uri} {fake_text[position_to_insert+2:]}'
            self.assertRegex(fake_text_uri, URL_PATTERN)
            self.assertNotIn(fake_uri, re.sub(URL_PATTERN, '', fake_text_uri))
            self.assertNotEqual(fake_text_uri, re.sub(URL_PATTERN, '', fake_text_uri))

        # Case found during testing on the ACC environment
        text = 'Just a couple of links in a piece of text, ' \
               'https://tweakers.net/reviews/8534/desktop-best-buy-guide-januari-2021.html and some more text. ' \
               'google.com www.nu.nl end of the test'
        self.assertRegex(text, URL_PATTERN)

        self.assertIn('https://tweakers.net/reviews/8534/desktop-best-buy-guide-januari-2021.html', text)
        self.assertIn('google.com', text)
        self.assertIn('www.nu.nl', text)

        text_with_no_links = re.sub(URL_PATTERN, '', text)
        self.assertNotRegex(text_with_no_links, URL_PATTERN)

        self.assertNotIn('https://tweakers.net/reviews/8534/desktop-best-buy-guide-januari-2021.html', text_with_no_links)  # noqa
        self.assertNotIn('google.com', text_with_no_links)
        self.assertNotIn('www.nu.nl', text_with_no_links)

    def test_make_email_context(self):
        signal = SignalFactory.create()
        context = make_email_context(signal=signal)

        self.assertEqual(context['signal_id'], signal.id)
        self.assertEqual(context['formatted_signal_id'], signal.sia_id)
        self.assertEqual(context['created_at'], signal.created_at)
        self.assertEqual(context['text'], signal.text)
        self.assertEqual(context['text_extra'], signal.text_extra)
        self.assertEqual(context['address'], signal.location.address)
        self.assertEqual(context['status_text'], signal.status.text)
        self.assertEqual(context['status_state'], signal.status.state)
        self.assertEqual(context['handling_message'], signal.category_assignment.stored_handling_message)
        self.assertEqual(context['ORGANIZATION_NAME'], settings.ORGANIZATION_NAME)

    def test_make_email_context_additional_context(self):
        signal = SignalFactory.create()
        context = make_email_context(signal=signal, additional_context={'extra': 'context'})

        self.assertEqual(context['signal_id'], signal.id)
        self.assertEqual(context['formatted_signal_id'], signal.sia_id)
        self.assertEqual(context['created_at'], signal.created_at)
        self.assertEqual(context['text'], signal.text)
        self.assertEqual(context['text_extra'], signal.text_extra)
        self.assertEqual(context['address'], signal.location.address)
        self.assertEqual(context['status_text'], signal.status.text)
        self.assertEqual(context['status_state'], signal.status.state)
        self.assertEqual(context['handling_message'], signal.category_assignment.stored_handling_message)
        self.assertEqual(context['ORGANIZATION_NAME'], settings.ORGANIZATION_NAME)
        self.assertEqual(context['extra'], 'context')

    def test_make_email_context_additional_context_should_not_override_default_variables(self):
        signal = SignalFactory.create()
        context = make_email_context(signal=signal, additional_context={'signal_id': 'test'})

        self.assertEqual(context['signal_id'], signal.id)
        self.assertNotEqual(context['signal_id'], 'test')

    def test_make_email_context_backwards_compatibility(self):
        """
        TODO: should be removed a.s.a.p.
        """
        signal = SignalFactory.create()
        context = make_email_context(signal=signal)

        self.assertEqual(context['signal'].id, signal.id)
        self.assertEqual(context['status']._signal_id, signal.id)
        self.assertEqual(context['status'].state, signal.status.state)

    def test_validate_email_template(self):
        email_template_valid = EmailTemplateFactory.create(key=EmailTemplate.SIGNAL_CREATED)
        result = validate_email_template(email_template_valid)
        self.assertTrue(result)

        email_template_invalid = EmailTemplateFactory.create(key=EmailTemplate.SIGNAL_STATUS_CHANGED_AFGEHANDELD,
                                                             title='{{ text|lower:"a" }}',  # TemplateSyntaxError
                                                             body='{{ created_at|date:"B" }}')  # NotImplementedError
        result = validate_email_template(email_template_invalid)
        self.assertFalse(result)

        email_template_invalid_title = EmailTemplateFactory.create(key=EmailTemplate.SIGNAL_STATUS_CHANGED_HEROPEND,
                                                                   title='{{ created_at|date:"B" }}')  # noqa NotImplementedError
        result = validate_email_template(email_template_invalid_title)
        self.assertFalse(result)

        email_template_invalid_body = EmailTemplateFactory.create(key=EmailTemplate.SIGNAL_STATUS_CHANGED_OPTIONAL,
                                                                  body='{{ created_at|date:"B" }}')  # noqa NotImplementedError
        result = validate_email_template(email_template_invalid_body)
        self.assertFalse(result)

    def test_validate_template(self):
        self.assertTrue(validate_template('{{ text|lower }}'))
        self.assertFalse(validate_template('{{ text|lower:"a" }}'))  # TemplateSyntaxError