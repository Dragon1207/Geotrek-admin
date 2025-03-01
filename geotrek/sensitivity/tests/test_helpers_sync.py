from io import StringIO
import shutil
import os
from unittest.mock import patch

from django.test import TestCase

from geotrek.common.tests.factories import FakeSyncCommand
from geotrek.sensitivity.tests.factories import SensitiveAreaFactory
from geotrek.sensitivity.helpers_sync import SyncRando


class SyncRandoTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.area = SensitiveAreaFactory.create(published=True)

    @patch('sys.stdout', new_callable=StringIO)
    def test_sensitivity(self, mock_stdout):
        command = FakeSyncCommand()
        synchro = SyncRando(command)
        synchro.sync('en')
        self.assertTrue(os.path.exists(os.path.join('var', 'tmp_sync_rando', 'api', 'en', 'sensitiveareas.geojson')))
        self.assertTrue(os.path.exists(os.path.join('var', 'tmp_sync_rando', 'api', 'en', 'sensitiveareas',
                                                    '{obj.pk}.kml'.format(obj=self.area))))

    def tearDown(self):
        if os.path.exists(os.path.join('var', 'tmp_sync_rando')):
            shutil.rmtree(os.path.join('var', 'tmp_sync_rando'))
