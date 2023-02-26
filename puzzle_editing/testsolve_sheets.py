import os
import random
import threading
import time
from unittest import skipIf

from django.conf import settings
from django.db import connection
from django.db import transaction
from django.db.utils import OperationalError
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

import google.auth
import google.oauth2
import googleapiclient.discovery
from googleapiclient.http import MediaFileUpload

from puzzle_editing.models import Puzzle
from puzzle_editing.models import TestsolveSession

CONFIG = settings.TESTSOLVE_SHEETS_CONFIG

creds = None

def get_google_credentials():
    global creds
    if creds is None:
        creds_path = os.path.join(
            settings.BASE_DIR,
            CONFIG["credentials_path"]
        )
        Credentials = google.oauth2.service_account.Credentials
        creds = Credentials.from_service_account_file(creds_path)
    return creds

def get_drive_api_client():
    return googleapiclient.discovery.build(
        "drive", "v3", credentials=get_google_credentials()
    )

def set_session_spreadsheet_link(session, spreadsheet_link):
    num_updated = 0
    try:
        # Do an atomic CAS to ensure that only one testsolve sheet
        # is persisted, even if multiple users attempt to create a
        # sheet at the same time. Other, unused sheets will be
        # deleted.
        num_updated = TestsolveSession.objects.filter(
            id=session.id,
            spreadsheet_link=""
        ).update(
            spreadsheet_link=spreadsheet_link
        )
    except OperationalError:
        # Too much concurrency. We're still okay if someone else made
        # the sheet before us.
        pass

    if num_updated == 0:
        # Either we failed, or someone else made the sheet before us.
        spreadsheet_link = TestsolveSession.objects.get(
            id=session.id
        ).spreadsheet_link
        # If we failed, return a server error.
        assert(spreadsheet_link != "")

    session.spreadsheet_link = spreadsheet_link
    return session.spreadsheet_link

def send_create_sheet_request(sheet_name):
    file_metadata = {
        "name": sheet_name,
        # Target MIME type. This tells Drive to convert the file
        # into the Google Sheets format instead of keeping it in
        # Office format.
        "mimeType": "application/vnd.google-apps.spreadsheet",
        # The folder that the file should be uploaded to.
        "parents": [CONFIG["folder_id"]],
    }
    spreadsheet_template_path = os.path.join(
        settings.BASE_DIR,
        CONFIG["spreadsheet_template_path"]
    )
    media = MediaFileUpload(
        spreadsheet_template_path,
        mimetype=CONFIG["spreadsheet_mimetype"],
        resumable=True
    )
    files_service = get_drive_api_client().files()
    return files_service.create(
        body=file_metadata,
        media_body=media,
        fields="id,webViewLink"
    ).execute()

def send_set_sheet_permissions_request(spreadsheet_id):
    permissions_service = get_drive_api_client().permissions()
    permissions_service.create(
        fileId=spreadsheet_id,
        body={
            "type": "anyone",
            "role": "writer",
        },
    ).execute()

def send_delete_sheet_request(spreadsheet_id):
    files_service = get_drive_api_client().files()
    files_service.delete(
        fileId=spreadsheet_id
    ).execute()

def share_folder(user_email):
    permissions_service = get_drive_api_client().permissions()
    permissions_service.create(
        fileId=CONFIG["folder_id"],
        sendNotificationEmail=False,
        body={
            "type": "user",
            "role": "writer",
            "emailAddress": user_email,
        },
    ).execute()

# If there already exists a sheet, returns None.
# Otherwise, returns the Google Sheets file ID of the newly
# created sheet.
# In both cases, create_testsolve_sheet ensures that
# session.spreadsheet_link links to the spreadshet associated
# with the session.
def create_testsolve_sheet(session):
    # If someone already made a sheet before us, we're good.
    if session.spreadsheet_link != "":
        return None

    # Optimistically create a sheet. If someone else creates
    # another sheet before us, we'll delete the sheet.
    file = send_create_sheet_request(
        f"TS {session.id}: {session.puzzle.name}.xlsx"
    )
    link = file.get("webViewLink")
    spreadsheet_id = file.get("id")

    try:
        send_set_sheet_permissions_request(spreadsheet_id)
        true_link = set_session_spreadsheet_link(session, link)
    except:
        send_delete_sheet_request(spreadsheet_id)
        raise

    if true_link != link:
        # This means that some one created another sheet before us.
        send_delete_sheet_request(spreadsheet_id)
        return None

    # Return the ID so that tests can clean up when we're done.
    return spreadsheet_id

@skipIf(not CONFIG["enabled"], "testsolve sheets feature not enabled")
class TestsolveSheetsTestCase(TransactionTestCase):
    def setUp(self):
        puz = Puzzle.objects.create(
            name="testpuz",
            status_mtime=timezone.now()
        )
        TestsolveSession.objects.create(puzzle=puz)
        self.errored = False
        self.spreadsheet_links = []
        self.spreadsheet_ids = []
        self.NUM_THREADS = 4

    def run_test_worker(self, func, tid):
        try:
            func(tid)
        except:
            self.errored = True
            raise

    def launch_threads(self, func):
        threads = []
        for i in range(self.NUM_THREADS):
            threads += [threading.Thread(
                target=self.run_test_worker,
                args=(func, i)
            )]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(self.errored, False)

    def run_simple_race_test(self, tid):
        spreadsheet_link = f"test {tid}"
        session = TestsolveSession.objects.get()
        spreadsheet_link = set_session_spreadsheet_link(
            session, spreadsheet_link
        )
        self.spreadsheet_links[tid] = spreadsheet_link

    def test_simple_race(self):
        self.spreadsheet_links = [None] * self.NUM_THREADS
        self.launch_threads(self.run_simple_race_test)
        for spreadsheet_link in self.spreadsheet_links:
            self.assertTrue(spreadsheet_link is not None)
            self.assertEqual(spreadsheet_link, self.spreadsheet_links[0])

    def run_create_sheet_race_test(self, tid):
        session = TestsolveSession.objects.get()
        spreadsheet_id = create_testsolve_sheet(session)
        self.spreadsheet_links[tid] = session.spreadsheet_link
        self.spreadsheet_ids[tid] = spreadsheet_id

    def test_create_sheet_race(self):
        self.spreadsheet_ids = [None] * self.NUM_THREADS
        self.spreadsheet_links = [None] * self.NUM_THREADS
        self.launch_threads(self.run_create_sheet_race_test)
        allocated = [x for x in self.spreadsheet_ids if x is not None]
        self.assertEqual(len(allocated), 1)
        for spreadsheet_link in self.spreadsheet_links:
            self.assertTrue(spreadsheet_link is not None)
            self.assertEqual(spreadsheet_link, self.spreadsheet_links[0])

    def tearDown(self):
        for spreadsheet_id in self.spreadsheet_ids:
            if spreadsheet_id is not None:
                send_delete_sheet_request(spreadsheet_id)
