from django.test import TestCase
from django.urls import reverse, resolve

USERNAME = 'user'
SLUG = 'test_group'
POST_ID = 1
NAMESPACE = resolve('/').namespace


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
            [f'/posts/{POST_ID}/comment/', 'add_comment', [POST_ID]],
            ['/follow/', 'follow_index', []],
            [f'/profile/{USERNAME}/follow/', 'profile_follow', [USERNAME]],
            [f'/profile/{USERNAME}/unfollow/', 'profile_unfollow', [USERNAME]],
        ]
        for natural, route, args in cases:
            with self.subTest(route=route):
                self.assertEqual(
                    reverse(f'{NAMESPACE}:{route}', args=args),
                    natural
                )
