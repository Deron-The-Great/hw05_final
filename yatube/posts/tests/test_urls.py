from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache

from posts.models import Post, Group, User, Follow

USERNAME = 'user'
AUTHOR_USERNAME = 'author'
POST_TEXT = 'Тестовый текст'
GROUP_SLUG = 'test_group'
GROUP_TITLE = 'Тестовый заголовок'
GROUP_DESCRIPTION = 'Тестовое описание'
POST_CREATE_URL = reverse('posts:post_create')
PROFILE_URL = reverse('posts:profile', args=[USERNAME])
GROUP_URL = reverse('posts:group_posts', args=[GROUP_SLUG])
MAIN_PAGE_URL = reverse('posts:index')
AUTHORISATION_URL = reverse('users:login')
ERROR_404 = '/404'
FOLLOW_URL = reverse('posts:follow_index')
PROFILE_FOLLOW_URL = reverse('posts:profile_follow', args=[USERNAME])
PROFILE_UNFOLLOW_URL = reverse('posts:profile_unfollow', args=[USERNAME])
AUTHOR_UNFOLLOW_URL = reverse('posts:profile_unfollow', args=[AUTHOR_USERNAME])
AUTHOR_FOLLOW_URL = reverse('posts:profile_follow', args=[AUTHOR_USERNAME])
AUTHOR_URL = reverse('posts:profile', args=[AUTHOR_USERNAME])


def authorisation_redirect(url):
    return f'{AUTHORISATION_URL}?next={url}'


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=USERNAME)
        cls.user_author = User.objects.create_user(username=AUTHOR_USERNAME)
        cls.group = Group.objects.create(
            slug=GROUP_SLUG,
            title=GROUP_TITLE,
            description=GROUP_DESCRIPTION
        )
        cls.post = Post.objects.create(
            text=POST_TEXT,
            author=cls.user_author,
            group=cls.group
        )
        cls.POST_EDIT_URL = reverse('posts:post_edit', args=[cls.post.pk])
        cls.POST_DETAIL_URL = reverse(
            'posts:post_detail',
            args=[cls.post.pk]
        )
        Follow.objects.create(user=cls.user, author=cls.user_author)
        cls.guest = Client()
        cls.author = Client()
        cls.author.force_login(cls.user_author)
        cls.another = Client()
        cls.another.force_login(cls.user)

    def test_urls_existing_at_desired_location(self):
        """Проверяем, что доступ к URL-адресам соответствует ожидаемому"""
        cases = [
            [MAIN_PAGE_URL, self.guest, 200],
            [GROUP_URL, self.guest, 200],
            [PROFILE_URL, self.guest, 200],
            [self.POST_DETAIL_URL, self.guest, 200],
            [self.POST_EDIT_URL, self.guest, 302],
            [POST_CREATE_URL, self.guest, 302],
            [ERROR_404, self.guest, 404],
            [self.POST_EDIT_URL, self.another, 302],
            [POST_CREATE_URL, self.another, 200],
            [self.POST_EDIT_URL, self.author, 200],
            [FOLLOW_URL, self.guest, 302],
            [FOLLOW_URL, self.another, 200],
            [AUTHOR_FOLLOW_URL, self.another, 302],
            [AUTHOR_UNFOLLOW_URL, self.guest, 302],
            [AUTHOR_UNFOLLOW_URL, self.author, 404],
            [AUTHOR_UNFOLLOW_URL, self.another, 302],
        ]
        for url, client, status_code in cases:
            with self.subTest(client=client, url=url):
                self.assertEqual(
                    client.get(url).status_code,
                    status_code
                )

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        cases = [
            [MAIN_PAGE_URL, self.author, 'posts/index.html'],
            [GROUP_URL, self.author, 'posts/group_list.html'],
            [PROFILE_URL, self.author, 'posts/profile.html'],
            [self.POST_DETAIL_URL, self.author,
             'posts/post_detail.html'],
            [self.POST_EDIT_URL, self.author, 'posts/create_post.html'],
            [POST_CREATE_URL, self.author, 'posts/create_post.html'],
            [ERROR_404, self.author, 'core/404.html'],
            [FOLLOW_URL, self.author, 'posts/follow.html']
        ]
        for url, client, template in cases:
            with self.subTest(client=client, url=url):
                cache.clear()
                self.assertTemplateUsed(
                    client.get(url),
                    template,
                )

    def test_urls_redirects_correctly(self):
        """URL-адрес использует корректную переадресацию."""
        cases = [
            [self.POST_EDIT_URL, self.guest,
             authorisation_redirect(self.POST_EDIT_URL)],
            [self.POST_EDIT_URL, self.another,
             self.POST_DETAIL_URL],
            [POST_CREATE_URL, self.guest,
             authorisation_redirect(POST_CREATE_URL)],
            [FOLLOW_URL, self.guest,
             authorisation_redirect(FOLLOW_URL)],
            [AUTHOR_FOLLOW_URL, self.another,
             AUTHOR_URL],
            [PROFILE_FOLLOW_URL, self.guest,
             authorisation_redirect(PROFILE_FOLLOW_URL)],
            [AUTHOR_UNFOLLOW_URL, self.another,
             AUTHOR_URL],
            [PROFILE_UNFOLLOW_URL, self.guest,
             authorisation_redirect(PROFILE_UNFOLLOW_URL)],
        ]
        for url, client, redirect_url in cases:
            with self.subTest(client=client, url=url):
                self.assertRedirects(client.get(url), redirect_url)
