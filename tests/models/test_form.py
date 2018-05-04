from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _
from modelcluster.models import ClusterableModel

from wagtail.core.models import Page

from wagtailstreamforms.conf import get_setting
from wagtailstreamforms.fields import HookSelectField
from wagtailstreamforms.models import Form, FormSubmission

from ..test_case import AppTestCase


class ModelGenericTests(AppTestCase):

    def test_inheritance(self):
        self.assertTrue(issubclass(Form, ClusterableModel))

    def test_str(self):
        model = Form(name='form')
        self.assertEqual(model.__str__(), model.name)

    def test_ordering(self):
        self.assertEqual(Form._meta.ordering, ['name', ])


class ModelFieldTests(AppTestCase):

    def test_name(self):
        field = self.get_field(Form, 'name')
        self.assertModelField(field, models.CharField)
        self.assertEqual(field.max_length, 255)

    def test_slug(self):
        field = self.get_field(Form, 'slug')
        self.assertModelField(field, models.SlugField)
        self.assertEqual(field.max_length, 255)
        self.assertTrue(field.allow_unicode)
        self.assertTrue(field.unique)

    def test_template_name(self):
        field = self.get_field(Form, 'template_name')
        self.assertModelField(field, models.CharField)
        self.assertEqual(field.max_length, 255)
        self.assertEqual(field.choices, get_setting('FORM_TEMPLATES'))

    def test_submit_button_text(self):
        field = self.get_field(Form, 'submit_button_text')
        self.assertModelField(field, models.CharField, False, False, 'Submit')
        self.assertEqual(field.max_length, 100)

    def test_success_message(self):
        field = self.get_field(Form, 'success_message')
        self.assertModelField(field, models.CharField, False, True)
        self.assertEqual(field.max_length, 255)

    def test_error_message(self):
        field = self.get_field(Form, 'error_message')
        self.assertModelField(field, models.CharField, False, True)
        self.assertEqual(field.max_length, 255)

    def test_post_redirect_page(self):
        field = self.get_field(Form, 'post_redirect_page')
        self.assertModelPKField(field, Page, models.SET_NULL, True, True)

    def test_process_form_submission_hooks(self):
        field = self.get_field(Form, 'process_form_submission_hooks')
        self.assertModelField(field, HookSelectField, False, True)


class ModelPropertyTests(AppTestCase):
    fixtures = ['test']

    def setUp(self):
        self.test_form = Form.objects.get(pk=1)

    def test_clean_raises_error_when_duplicate_slug(self):
        new_form = Form(name=self.test_form.name, slug=self.test_form.slug, template_name=self.test_form.template_name)

        with self.assertRaises(ValidationError) as cm:
            new_form.full_clean()

        self.assertEqual(
            cm.exception.message_dict,
            {'slug': ['Form with this Slug already exists.']}
        )

    def test_copy(self):
        copied = self.test_form.copy()

        self.assertNotEqual(copied.pk, self.test_form.pk)
        self.assertEqual(copied.__class__, self.test_form.__class__)

    def test_copy_has_form_fields(self):
        copied = self.test_form.copy()

        self.assertListEqual(
            [field['type'] for field in copied.get_form_fields()],
            [
                'singleline',
                'multiline',
                'date',
                'datetime',
                'email',
                'url',
                'number',
                'dropdown',
                'multiselect',
                'radio',
                'checkboxes',
                'checkbox',
                'hidden'
            ]
        )

    def test_copy_does_not_copy_form_submissions(self):
        # it should never do any way as its a reverse fk but incase modelcluster
        # ever changes we are testing for it

        FormSubmission.objects.create(form_data='{}', form=self.test_form)

        copied = self.test_form.copy()

        self.assertEqual(FormSubmission.objects.filter(form=copied).count(), 0)

    def test_get_data_fields(self):
        expected_fields = [
            ('submit_time', _('Submission date')),
            ('singleline', _('singleline')),
            ('multiline', _('multiline')),
            ('date', _('date')),
            ('datetime', _('datetime')),
            ('email', _('email')),
            ('url', _('url')),
            ('number', _('number')),
            ('dropdown', _('dropdown')),
            ('multiselect', _('multiselect')),
            ('radio', _('radio')),
            ('checkboxes', _('checkboxes')),
            ('checkbox', _('checkbox')),
            ('hidden', _('hidden'))
        ]
        self.assertEqual(self.test_form.get_data_fields(), expected_fields)

    def test_get_form(self):
        actual_fields = [f for f in self.test_form.get_form().fields]
        expected_fields = [
            'singleline',
            'multiline',
            'date',
            'datetime',
            'email',
            'url',
            'number',
            'dropdown',
            'multiselect',
            'radio',
            'checkboxes',
            'checkbox',
            'hidden',
            'form_id',
            'form_reference'
        ]
        self.assertEqual(actual_fields, expected_fields)

    def test_get_form_fields(self):
        self.assertListEqual(
            [field['type'] for field in self.test_form.get_form_fields()],
            [
                'singleline',
                'multiline',
                'date',
                'datetime',
                'email',
                'url',
                'number',
                'dropdown',
                'multiselect',
                'radio',
                'checkboxes',
                'checkbox',
                'hidden'
            ]
        )

    def test_get_form_parameters(self):
        form = Form()
        self.assertEqual(form.get_form_parameters(), {})

    def test_get_submission_class(self):
        self.assertEqual(self.test_form.get_submission_class(), FormSubmission)

    def test_process_form_submission(self):
        def complete_hook(instance, form):
            instance._completed = True

        with self.register_hook('process_form_submission', complete_hook, order=-1):
            form_class = self.test_form.get_form_class()

            # wont call registered hooks that are not saved
            self.test_form.process_form_submission(form_class)
            self.assertFalse(hasattr(self.test_form, '_completed'))

            # selected hooks
            self.test_form.process_form_submission_hooks = ['complete_hook']
            self.test_form.save()

            self.test_form.process_form_submission(form_class)
            self.assertTrue(self.test_form._completed)
