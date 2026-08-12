"""Компонент серверной части GeoMap."""

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from points.auth import authenticate_telegram_user
from points.geo import parse_bounds
from points.models import Point, PointType
from users.models import TelegramProfile


@override_settings(BOT_API_KEY='test-bot-key')
class AdminPointTypeTests(TestCase):
    """Класс, инкапсулирующий логику серверного компонента GeoMap."""
    def setUp(self):
        """Выполняет операцию серверного компонента GeoMap."""
        self.client = APIClient()
        user = User.objects.create_user(username='tg_100')
        TelegramProfile.objects.create(
            user=user,
            telegram_id=100,
            role=TelegramProfile.Role.SUPERUSER,
        )

    def test_admin_can_create_point_type(self):
        """Выполняет операцию серверного компонента GeoMap."""
        response = self.client.post(
            '/api/admin/point-types/?telegram_user_id=100',
            {
                'name': 'warehouse',
                'icon_name': 'Warehouse',
                'show_on_main_map': False,
            },
            format='json',
            HTTP_AUTHORIZATION='Api-Key test-bot-key',
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(PointType.objects.filter(name='warehouse').exists())


class TelegramAuthRegressionTests(TestCase):
    """Класс, инкапсулирующий логику серверного компонента GeoMap."""
    def test_authentication_does_not_collect_phone_number(self):
        """Выполняет операцию серверного компонента GeoMap."""
        authenticate_telegram_user(
            telegram_id=200,
            username='new_user',
            first_name='New',
        )

        profile = TelegramProfile.objects.get(telegram_id=200)
        self.assertEqual(profile.phone_number, '')


class ViewportTests(TestCase):
    """Класс, инкапсулирующий логику серверного компонента GeoMap."""
    def setUp(self):
        """Выполняет операцию серверного компонента GeoMap."""
        public_type = PointType.objects.create(name='public')
        Point.objects.create(
            title='Inside',
            point_type=public_type,
            lat=56.01,
            lng=92.86,
            telegram_user_id=1,
        )
        Point.objects.create(
            title='Outside',
            point_type=public_type,
            lat=56.20,
            lng=93.10,
            telegram_user_id=1,
        )

    def test_bounds_parser_rejects_invalid_coordinates(self):
        """Выполняет операцию серверного компонента GeoMap."""
        self.assertIsNone(parse_bounds('92,-90,93,91'))
        self.assertEqual(
            parse_bounds('92.8,55.9,92.9,56.1'),
            {'west': 92.8, 'south': 55.9, 'east': 92.9, 'north': 56.1},
        )

    def test_points_endpoint_filters_by_bbox(self):
        """Выполняет операцию серверного компонента GeoMap."""
        response = self.client.get('/api/points/?bbox=92.8,55.9,92.9,56.1')

        self.assertEqual(response.status_code, 200)
        payload = response.data
        points = payload['results'] if isinstance(payload, dict) else payload
        self.assertEqual([point['title'] for point in points], ['Inside'])
