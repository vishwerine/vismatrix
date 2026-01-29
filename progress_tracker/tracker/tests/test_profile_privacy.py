from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from ..models import UserActivity, Task


class ActivityPrivacyToggleTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='tester', password='pass')
        self.client.login(username='tester', password='pass')

    def test_toggle_visibility_success(self):
        # create activity
        activity = UserActivity.objects.create(
            user=self.user,
            activity_type='task_completed',
            visibility='friends'
        )

        url = reverse('toggle_activity_privacy', kwargs={'activity_id': activity.id})
        response = self.client.post(url, {'visibility': 'private'})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get('success'))

        # reload from db
        activity.refresh_from_db()
        self.assertEqual(activity.visibility, 'private')

    def test_toggle_visibility_invalid_choice(self):
        activity = UserActivity.objects.create(
            user=self.user,
            activity_type='task_completed',
            visibility='friends'
        )

        url = reverse('toggle_activity_privacy', kwargs={'activity_id': activity.id})
        response = self.client.post(url, {'visibility': 'unknown'})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data.get('success'))
        self.assertIn('error', data)

    def test_toggle_propagates_to_task(self):
        # create task and activity linked to it
        task = Task.objects.create(user=self.user, title='T1', status='completed', visibility='friends')
        activity = UserActivity.objects.create(
            user=self.user,
            activity_type='task_completed',
            task=task,
            visibility='friends'
        )

        url = reverse('toggle_activity_privacy', kwargs={'activity_id': activity.id})
        response = self.client.post(url, {'visibility': 'private'})
        self.assertEqual(response.status_code, 200)
        activity.refresh_from_db()
        task.refresh_from_db()
        self.assertEqual(activity.visibility, 'private')
        self.assertEqual(task.visibility, 'private')
