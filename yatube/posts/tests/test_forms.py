import shutil
import tempfile

from django import forms
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from posts.models import Post, Group, User, Comment
from posts.tests.test_urls import authorisation_redirect

USERNAME = 'username'
NOT_AUTHOR = 'not_author'
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
        cls.not_author = User.objects.create_user(username=NOT_AUTHOR)
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
        cls.image = SimpleUploadedFile(
            name='small.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        )
        cls.post = Post.objects.create(
            text=TEXT_OLD,
            author=cls.user,
            group=cls.group,
            image=cls.image
        )
        cls.POST_EDIT_URL = reverse('posts:post_edit', args=[cls.post.pk])
        cls.POST_DETAIL_URL = reverse(
            'posts:post_detail',
            args=[cls.post.id]
        )
        cls.ADD_COMENT_URL = reverse('posts:add_comment', args=[cls.post.pk])
        cls.images = [SimpleUploadedFile(
            name=f'small{i}.gif',
            content=SMALL_GIF,
            content_type='image/gif'
        ) for i in range(4)]
        cls.guest_client = Client()
        cls.user_client = Client()
        cls.user_client.force_login(cls.user)
        cls.not_author_client = Client()
        cls.not_author_client.force_login(cls.not_author)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post_user(self):
        """Тест на добавление записи в базу данных по валидной форме."""
        posts = set(Post.objects.all())
        post_form = {
            'text': TEXT_NEW,
            'group': self.group.id,
            'image': self.images[0]
        }
        request = self.user_client.post(
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
        self.assertEqual(
            post.image.name,
            f'{Post._meta.get_field("image").upload_to}{self.images[0].name}'
        )
        self.assertRedirects(request, PROFILE_URL)

    def test_create_post_guest(self):
        posts_before = set(Post.objects.all())
        post_form = {
            'text': TEXT_NEW,
            'group': self.group.id,
            'image': self.images[1]
        }
        request = self.guest_client.post(
            POST_CREATE_URL,
            data=post_form,
            follow=True
        )
        posts_after = set(Post.objects.all())
        self.assertEqual(posts_before, posts_after)
        self.assertRedirects(request, authorisation_redirect(POST_CREATE_URL))

    def test_edit_post_user(self):
        """Тест на изменение записи в базе данных по валидной форме."""
        post_form = {
            'text': TEXT_NEW,
            'group': self.another_group.id,
            'image': self.images[2]
        }
        response = self.user_client.post(
            self.POST_EDIT_URL,
            data=post_form,
            follow=True
        )
        post = Post.objects.get(pk=self.post.pk)
        self.assertEqual(post.text, post_form['text'])
        self.assertEqual(post.group.id, post_form['group'])
        self.assertEqual(post.author, self.post.author)
        self.assertEqual(
            post.image.name,
            f'{Post._meta.get_field("image").upload_to}{self.images[2].name}'
        )
        self.assertRedirects(response, self.POST_DETAIL_URL)

    def test_edit_post_not_author(self):
        post_form = {
            'text': TEXT_NEW,
            'group': self.another_group.id,
            'image': self.images[3]
        }
        cases = [
            [self.guest_client, authorisation_redirect(self.POST_EDIT_URL)],
            [self.not_author_client, self.POST_DETAIL_URL]
        ]
        for client, redirrect in cases:
            with self.subTest(client=client):
                response = client.post(
                    self.POST_EDIT_URL,
                    data=post_form,
                    follow=True
                )
                post = Post.objects.get(pk=self.post.pk)
                self.assertEqual(post.text, self.post.text)
                self.assertEqual(post.group, self.post.group)
                self.assertEqual(post.author, self.post.author)
                self.assertEqual(post.image.name, self.post.image.name)
                self.assertRedirects(response, redirrect)

    def test_post_create_uses_correct_context(self):
        """URL-адрес создания записи использует соответствующий контекст."""
        urls = [POST_CREATE_URL, self.POST_EDIT_URL]
        for url in urls:
            request = self.user_client.get(url).context.get('form')
            for value, expected in FORM_FIELDS.items():
                with self.subTest(url=url, value=value):
                    self.assertIsInstance(
                        request.fields.get(value),
                        expected
                    )

    def test_add_comment_guest(self):
        """Проверяем, что доступ к URL-адресам соответствует ожидаемому"""
        comments = len(Comment.objects.all())
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
            authorisation_redirect(self.ADD_COMENT_URL)
        )
        self.assertEqual(len(Comment.objects.all()) - comments, 0)

    def test_add_comment_user(self):
        comments = set(Comment.objects.all())
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
        set_difference = set(Comment.objects.all()).difference(comments)
        self.assertEqual(len(set_difference), 1)
        comment = set_difference.pop()
        self.assertEqual(comment.author, self.user)
        self.assertEqual(comment.text, post_form['text'])
        self.assertEqual(comment.post, self.post)
