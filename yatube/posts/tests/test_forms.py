import shutil
import tempfile

from django import forms
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from posts.models import Post, Group, User, Comment

USERNAME = 'username'
GROUP_SLUGS = ['test_group', 'another_group']
GROUP_TITLES = ['Тестовый заголовок 1', 'Тестовый заголовок 2']
GROUP_DESCTIPTIONS = ['Тестовое описание 1', 'Тестовое описание 2']
POST_CREATE_URL = reverse('posts:post_create')
PROFILE_URL = reverse('posts:profile', args=[USERNAME])
TEXT_OLD = 'Старая запись'
TEXT_NEW = 'Новая запись'
COMMENT_TEXT = 'Текст комментария'
AUTHORISATION_URL = reverse('users:login')
FORM_FIELDS = {
    'text': forms.fields.CharField,
    'group': forms.fields.ChoiceField,
    'image': forms.fields.ImageField
}
SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x01\x00'
    b'\x01\x00\x00\x00\x00\x21\xf9\x04'
    b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
    b'\x00\x00\x01\x00\x01\x00\x00\x02'
    b'\x02\x4c\x01\x00\x3b'
)
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=USERNAME)
        cls.group = Group.objects.create(
            slug=GROUP_SLUGS[0],
            title=GROUP_TITLES[0],
            description=GROUP_DESCTIPTIONS[0]
        )
        cls.another_group = Group.objects.create(
            slug=GROUP_SLUGS[1],
            title=GROUP_TITLES[1],
            description=GROUP_DESCTIPTIONS[1]
        )
        cls.post = Post.objects.create(
            text=TEXT_OLD,
            author=cls.user,
            group=cls.group
        )
        cls.POST_EDIT_URL = reverse('posts:post_edit', args=[cls.post.pk])
        cls.POST_DETAIL_URL = reverse(
            'posts:post_detail',
            args=[cls.post.id]
        )
        cls.image = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.user)
        self.posts_count = Post.objects.count()

    def test_creating_post_new_post_in_db(self):
        """Тест на добавление записи в базу данных по валидной форме."""
        posts = set(Post.objects.all())
        post_form = {
            'text': TEXT_NEW,
            'group': self.group.id,
            'image': self.image
        }
        response = self.client.post(
            POST_CREATE_URL,
            data=post_form,
            follow=True
        )
        set_difference = set(Post.objects.all()).difference(posts)
        self.assertEqual(len(set_difference), 1)
        post = set_difference.pop()
        self.assertEqual(post.text, post_form['text'])
        self.assertEqual(post.group.id, post_form['group'])
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.image.name, f'posts/{self.image.name}')
        self.assertRedirects(response, PROFILE_URL)

    def test_edit_post_old_post_in_db(self):
        """Тест на изменение записи в базе данных по валидной форме."""
        post_form = {
            'text': TEXT_NEW,
            'group': self.another_group.id
        }
        response = self.client.post(
            self.POST_EDIT_URL,
            data=post_form,
            follow=True
        )
        post = response.context.get('post')
        self.assertEqual(post.text, post_form['text'])
        self.assertEqual(post.group.id, post_form['group'])
        self.assertEqual(post.author, self.post.author)
        self.assertRedirects(response, self.POST_DETAIL_URL)

    def test_post_create_uses_correct_context(self):
        """URL-адрес создания записи использует соответствующий контекст."""
        urls = [POST_CREATE_URL, self.POST_EDIT_URL]
        for url in urls:
            request = self.client.get(url).context.get('form')
            for value, expected in FORM_FIELDS.items():
                with self.subTest(url=url, value=value):
                    self.assertIsInstance(
                        request.fields.get(value),
                        expected
                    )


class PostsCommentsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=USERNAME)
        cls.post = Post.objects.create(
            text=TEXT_OLD,
            author=cls.user
        )
        cls.POST_DETAIL_URL = reverse(
            'posts:post_detail',
            args=[cls.post.pk]
        )
        cls.ADD_COMENT_URL = reverse('posts:add_comment', args=[cls.post.pk])

    def setUp(self):
        self.guest_client = Client()
        self.user_client = Client()
        self.user_client.force_login(self.user)

    def test_add_comment_guest(self):
        """Проверяем, что доступ к URL-адресам соответствует ожидаемому"""
        post_form = {
            'text': COMMENT_TEXT,
        }
        response = self.guest_client.post(
            self.ADD_COMENT_URL,
            data=post_form,
            follow=True
        )
        self.assertRedirects(
            response,
            f'{AUTHORISATION_URL}?next={self.ADD_COMENT_URL}'
        )
        self.assertEqual(len(Comment.objects.all()), 0)

    def test_add_comment_user(self):
        post_form = {
            'text': COMMENT_TEXT,
        }
        response = self.user_client.post(
            self.ADD_COMENT_URL,
            data=post_form,
            follow=True
        )
        self.assertRedirects(
            response,
            self.POST_DETAIL_URL
        )
        self.assertEqual(len(Comment.objects.all()), 1)
        comments = response.context.get('comments')
        self.assertEqual(len(comments), 1)
        comment = comments[0]
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.text, post_form['text'])