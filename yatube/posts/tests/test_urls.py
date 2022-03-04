from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache

from posts.models import Post, Group, User

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
NOT_EXSIST_URL = '/not_exsist/'
AUTHORISATION_URL = reverse('users:login')
ERROR_404 = '/404'


def authorisation_redirect(url):
    return f'{AUTHORISATION_URL}?next={url}'


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=USERNAME)
        cls.author = User.objects.create_user(username=AUTHOR_USERNAME)
        cls.group = Group.objects.create(
            slug=GROUP_SLUG,
            title=GROUP_TITLE,
            description=GROUP_DESCRIPTION
        )
        cls.post = Post.objects.create(
            text=POST_TEXT,
            author=cls.author,
            group=cls.group
        )
        cls.POST_EDIT_URL = reverse('posts:post_edit', args=[cls.post.pk])
        cls.POST_DETAIL_URL = reverse(
            'posts:post_detail',
            args=[cls.post.pk]
        )
        cls.ADD_COMENT_URL = reverse('posts:add_comment', args=[cls.post.pk])

    def setUp(self):
        self.guest_client = Client()
        self.author_client = Client()
        self.author_client.force_login(self.author)
        self.user_client = Client()
        self.user_client.force_login(self.user)

    def test_urls_existing_at_desired_location(self):
        """Проверяем, что доступ к URL-адресам соответствует ожидаемому"""
        cases = [
            [MAIN_PAGE_URL, self.guest_client, 200],
            [GROUP_URL, self.guest_client, 200],
            [PROFILE_URL, self.guest_client, 200],
            [self.POST_DETAIL_URL, self.guest_client, 200],
            [self.POST_EDIT_URL, self.guest_client, 302],
            [POST_CREATE_URL, self.guest_client, 302],
            [NOT_EXSIST_URL, self.guest_client, 404],
            [self.POST_EDIT_URL, self.user_client, 302],
            [POST_CREATE_URL, self.user_client, 200],
            [self.POST_EDIT_URL, self.author_client, 200],
        ]
        for url, client, status_code in cases:
            with self.subTest(client=client, url=url):
                self.assertEqual(
                    client.get(url).status_code,
                    status_code
                )

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        author_client = self.author_client
        cases = [
            [MAIN_PAGE_URL, author_client, 'posts/index.html'],
            [GROUP_URL, author_client, 'posts/group_list.html'],
            [PROFILE_URL, author_client, 'posts/profile.html'],
            [self.POST_DETAIL_URL, author_client, 'posts/post_detail.html'],
            [self.POST_EDIT_URL, author_client, 'posts/create_post.html'],
            [POST_CREATE_URL, author_client, 'posts/create_post.html'],
            [ERROR_404, author_client, 'core/404.html']
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
            [
                self.POST_EDIT_URL,
                self.guest_client,
                authorisation_redirect(self.POST_EDIT_URL)
            ],
            [
                self.POST_EDIT_URL,
                self.user_client,
                self.POST_DETAIL_URL
            ],
            [
                POST_CREATE_URL,
                self.guest_client,
                authorisation_redirect(POST_CREATE_URL)
            ],
        ]
        for url, client, redirect_url in cases:
            with self.subTest(client=client, url=url):
                self.assertRedirects(client.get(url), redirect_url)
