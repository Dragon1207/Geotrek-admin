"""
    Unit tests
"""
from .base import AuthentFixturesTest
from django.urls import reverse

from geotrek.authent.tests.factories import StructureFactory, PathManagerFactory
from geotrek.core.tests.factories import PathFactory
from geotrek.common.tests.factories import AttachmentFactory
from geotrek.common.utils.testdata import get_dummy_uploaded_image


class StructureTest(AuthentFixturesTest):

    def test_basic(self):
        s = StructureFactory(name="Mércäntour")
        self.assertEqual(str(s), "Mércäntour")

    def test_structure_restricted(self):
        p = PathFactory()
        # Login
        user = PathManagerFactory(password="foo")
        success = self.client.login(username=user.username, password="foo")
        self.assertTrue(success)
        # Try to edit path from same structure
        response = self.client.get(p.get_update_url())
        self.assertEqual(response.status_code, 200)
        # Try to edit path from other structure
        p.structure = StructureFactory(name="Other")
        p.save()
        self.assertNotEqual(p.structure, user.profile.structure)
        response = self.client.get(p.get_update_url())
        self.assertEqual(response.status_code, 302)

    def test_structure_restricted_attachment(self):
        """Attachment should not be modified"""
        p = PathFactory()
        picture = AttachmentFactory(content_object=p, title='img1',
                                    attachment_file=get_dummy_uploaded_image())
        # Login
        user = PathManagerFactory(password="foo")
        self.client.login(username=user.username, password="foo")

        # Add an attachment to path from same structure
        update_attachment_url = reverse(
            'update_attachment',
            kwargs={'attachment_pk': picture.pk}
        )
        response = self.client.get(update_attachment_url)
        self.assertEqual(response.status_code, 200)

        # Add attachment or remove existing one from other structure
        p.structure = StructureFactory(name="Other")
        p.save()
        self.assertNotEqual(p.structure, user.profile.structure)

        response = self.client.get(update_attachment_url)
        self.assertEqual(response.status_code, 302)
