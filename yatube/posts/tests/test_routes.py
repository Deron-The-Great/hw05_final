from django.test import TestCase
from django.urls import reverse

USERNAME = 'user'
SLUG = 'test_group'
POST_ID = 1


class RoutesTest(TestCase):
    def test_routes(self):
        """Проверяет правильность вычисления маршрутов."""
        cases = [
            ['/', 'index', []],
            [f'/group/{SLUG}/', 'group_posts', [SLUG]],
            [f'/profile/{USERNAME}/', 'profile', [USERNAME]],
            [f'/posts/{POST_ID}/', 'post_detail', [POST_ID]],
            [f'/posts/{POST_ID}/edit/', 'post_edit', [POST_ID]],
            ['/create/', 'post_create', []],
        ]
        for natural, route, args in cases:
            with self.subTest(route=route):
                self.assertEqual(
                    reverse(f'posts:{route}', args=args),
                    natural
                )
