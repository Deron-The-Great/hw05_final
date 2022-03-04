import shutil
import tempfile

from django.test import Client, TestCase, override_settings
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from posts.models import Follow, Post, Group, User
from yatube.settings import POSTS_PER_PAGE

USERNAME = 'username'
FOLLOWER_USERNAME = 'follower'
UNFOLLOWER_USERNAME = 'unfollower'
POST_TEXT = 'Тестовый текст'
GROUP_SLUG = 'test_group'
GROUP_TITLE = 'Тестовый заголовок'
GROUP_DESCRIPTION = 'Тестовое описание'
POST_CREATE_URL = reverse('posts:post_create')
PROFILE_URL = reverse('posts:profile', args=[USERNAME])
GROUP_URL = reverse('posts:group_posts', args=[GROUP_SLUG])
MAIN_PAGE_URL = reverse('posts:index')
AUTHORISATION_URL = reverse('users:login')
NEW_GROUP_SLUG = 'new_group'
NEW_GROUP_TITLE = 'Новый тестовый заголовок'
NEW_GROUP_DESCRIPTION = 'Новое тестовое описание'
NEW_GROUP_URL = reverse('posts:group_posts', args=[NEW_GROUP_SLUG])
SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00'
    b'\x01\x00\x00\x00\x00\x21\xf9\x04'
    b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
    b'\x00\x00\x01\x00\x01\x00\x00\x02'
    b'\x02\x4c\x01\x00\x3b'
)
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
FOLLOW_INDEX_URL = reverse('posts:follow_index')
FOLLOW_URL = reverse('posts:profile_follow', args=[USERNAME])
UNFOLLOW_URL = reverse('posts:profile_unfollow', args=[USERNAME])


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.image = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username=USERNAME)
        cls.group = Group.objects.create(
            slug=GROUP_SLUG,
            title=GROUP_TITLE,
            description=GROUP_DESCRIPTION
        )
        cls.post = Post.objects.create(
            text=POST_TEXT,
            author=cls.user,
            group=cls.group,
            image=cls.image
        )
        cls.follower = User.objects.create_user(username=FOLLOWER_USERNAME)
        cls.unfollower = User.objects.create_user(username=UNFOLLOWER_USERNAME)
        cls.POST_EDIT_URL = reverse('posts:post_edit', args=[cls.post.pk])
        cls.POST_DETAIL_URL = reverse(
            'posts:post_detail',
            args=[cls.post.pk]
        )
        Follow.objects.create(user=cls.follower, author=cls.user)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)
        self.follower_client = Client()
        self.follower_client.force_login(self.follower)
        self.unfollower_client = Client()
        self.unfollower_client.force_login(self.unfollower)

    def test_pages_uses_correct_context(self):
        """Страницы содержат правильный контекст."""
        urls = [MAIN_PAGE_URL, GROUP_URL, PROFILE_URL, self.POST_DETAIL_URL]
        for url in urls:
            with self.subTest(url=url):
                context = self.client.get(url).context
                if url != self.POST_DETAIL_URL:
                    self.assertEqual(len(context.get('page_obj')), 1)
                    post = context.get('page_obj')[0]
                else:
                    post = context.get('post')
                self.assertEqual(post.id, self.post.id)
                self.assertEqual(post.text, self.post.text)
                self.assertEqual(post.author, self.post.author)
                self.assertEqual(post.group, self.post.group)
                self.assertEqual(post.image.name, f'posts/{self.image.name}')

    def test_post_groups_uses_correct_context(self):
        """Страница группы содержит правильную группу."""
        group = self.client.get(GROUP_URL).context.get('group')
        self.assertEqual(group.id, self.post.group.id)
        self.assertEqual(group.slug, self.post.group.slug)
        self.assertEqual(group.title, self.post.group.title)
        self.assertEqual(group.description, self.post.group.description)

    def test_profile_uses_correct_context(self):
        """Страница профиля содержит правильного автора."""
        author = self.client.get(PROFILE_URL).context.get('author')
        self.assertEqual(author, self.post.author)

    def test_another_group_page_not_contains_created_post(self):
        """Страницы других групп не содержат созданную запись."""
        self.another_group = Group.objects.create(
            slug=NEW_GROUP_SLUG,
            title=NEW_GROUP_TITLE,
            description=NEW_GROUP_DESCRIPTION
        )
        self.assertNotIn(
            self.post,
            self.client.get(NEW_GROUP_URL).context.get('page_obj')
        )

    def test_page_contains_records(self):
        """Страница содержит нужное количество записей."""
        Post.objects.bulk_create(
            [Post(
                text=f'{POST_TEXT} {i+1}',
                author=self.user,
                group=self.group
            ) for i in range(POSTS_PER_PAGE)]
        )
        # один пост изначально есть в базе
        cases = [
            [MAIN_PAGE_URL, POSTS_PER_PAGE],
            [GROUP_URL, POSTS_PER_PAGE],
            [PROFILE_URL, POSTS_PER_PAGE],
            [f'{MAIN_PAGE_URL}?page=2', 1],
            [f'{GROUP_URL}?page=2', 1],
            [f'{PROFILE_URL}?page=2', 1],
        ]
        for url, posts_on_page in cases:
            with self.subTest(url=url):
                cache.clear()
                self.assertEqual(
                    len(self.client.get(url).context['page_obj']),
                    posts_on_page
                )

    def test_index_cache(self):
        content_one = self.client.get(MAIN_PAGE_URL).content
        Post.objects.create(
            text=POST_TEXT,
            author=self.user,
            group=self.group,
            image=self.image
        )
        content_two = self.client.get(MAIN_PAGE_URL).content
        self.assertEqual(content_one, content_two)
        cache.clear()
        content_three = self.client.get(MAIN_PAGE_URL).content
        self.assertNotEqual(content_one, content_three)

    def test_follow(self):
        len_follow = len(Follow.objects.all())
        request = self.unfollower_client.post(
            FOLLOW_URL,
            follow=True
        )
        self.assertEqual(len(Follow.objects.all()) - len_follow, 1)
        self.assertRedirects(request, PROFILE_URL)

    def test_unfollow(self):
        len_follow = len(Follow.objects.all())
        request = self.follower_client.post(
            UNFOLLOW_URL,
            follow=True
        )
        self.assertEqual(len(Follow.objects.all()) - len_follow, -1)
        self.assertRedirects(request, PROFILE_URL)

    def test_follow_index(self):
        context = self.follower_client.get(FOLLOW_INDEX_URL).context
        self.assertEqual(len(context.get('page_obj')), 1)
        post = context.get('page_obj')[0]
        self.assertEqual(post.id, self.post.id)
        self.assertEqual(post.text, self.post.text)
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(post.group, self.post.group)
        self.assertEqual(post.image.name, f'posts/{self.image.name}')
        context = self.unfollower_client.get(FOLLOW_INDEX_URL).context
        self.assertEqual(len(context.get('page_obj')), 0)
