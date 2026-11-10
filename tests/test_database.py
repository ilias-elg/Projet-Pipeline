import logging
import unittest

from processing import extract_transform as et
from settings import SETTINGS
from storage import database

# Pas d'écriture dans logs/ pendant les tests
logging.disable(logging.CRITICAL)

HEADER = 'May 24 01:14:12 ns sshd[1]: '


class TestDatabase(unittest.TestCase):

    def test_unreachable_database_does_not_crash(self):
        wrong = dict(SETTINGS['database'], port=1)  # aucun serveur sur le port 1
        self.assertIsNone(database.connect(wrong))

    def test_save_and_load_roundtrip(self):
        # Base de test séparée pour ne pas effacer les vraies données
        connection = database.connect(dict(SETTINGS['database'], dbname='postgres'))
        if connection is None:
            self.skipTest('PostgreSQL not available')
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute("DROP DATABASE IF EXISTS log_analysis_test")
            cursor.execute("CREATE DATABASE log_analysis_test")
        connection.close()

        test_db = database.connect(dict(SETTINGS['database'], dbname='log_analysis_test'))
        try:
            events = et.transform([
                HEADER + 'Accepted password for alice from 10.0.0.1 port 1 ssh2',
                HEADER + 'message repeated 3 times: [ Failed password for root from 1.1.1.1 port 1 ssh2]',
                HEADER + 'Failed password for invalid user admin from 2.2.2.2 port 1 ssh2',
            ])
            events[1]['country'] = 'AU'
            self.assertTrue(database.save_events(events, test_db))
            self.assertTrue(database.save_geolocation({'1.1.1.1': 'AU'}, test_db))
            loaded = database.load_events(test_db)
            self.assertEqual(len(loaded), 3)
            self.assertEqual(loaded[0]['user'], 'alice')
            self.assertEqual(loaded[1]['count'], 3)
            self.assertEqual(loaded[1]['country'], 'AU')
            self.assertTrue(loaded[2]['invalid_user'])
            self.assertEqual(loaded[0]['date'], events[0]['date'])
        finally:
            test_db.close()


if __name__ == '__main__':
    unittest.main()
