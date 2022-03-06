from django.contrib.auth import get_user_model
from django.db import models
from django.forms import ValidationError

User = get_user_model()


class Group(models.Model):
    slug = models.SlugField(
        verbose_name='Текстовый идентификатор страницы',
        max_length=200,
        unique=True
    )
    title = models.CharField(verbose_name='Заголовок', max_length=200)
    description = models.TextField(verbose_name='Описание')

    class Meta:
        verbose_name = 'Группа'
        verbose_name_plural = 'Группы'

    def __str__(self):
        return self.title


class Post(models.Model):
    text = models.TextField(
        verbose_name='Текст',
        help_text='Введите текст записи'
    )
    pub_date = models.DateTimeField(
        verbose_name='Дата публикации',
        auto_now_add=True
    )
    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='posts',
    )
    group = models.ForeignKey(
        Group,
        verbose_name='Группа',
        on_delete=models.SET_NULL,
        related_name='posts',
        blank=True,
        null=True,
        help_text='Группа, к которой будет относиться запись'
    )
    image = models.ImageField(
        verbose_name='Картинка',
        upload_to='posts/',
        blank=True,
        null=True,
        help_text='Картинка иллюстрирующая запись'
    )

    class Meta:
        ordering = ('-pub_date',)
        verbose_name = 'Запись'
        verbose_name_plural = 'Записи'

    def __str__(self):
        return self.text[:15]


class Comment(models.Model):
    text = models.TextField(
        verbose_name='Текст',
        help_text='Введите текст записи'
    )
    post = models.ForeignKey(
        Post,
        verbose_name='Запись',
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='comments',
    )
    created = models.DateTimeField(
        verbose_name='Дата публикации',
        auto_now_add=True
    )

    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Пользователь',
        on_delete=models.CASCADE,
        related_name='follower'
    )
    author = models.ForeignKey(
        User,
        verbose_name='Автор',
        on_delete=models.CASCADE,
        related_name='following'
    )

    def clean(self):
        if Follow(user=self.user, author=self.author) in Follow.objects.all():
            raise ValidationError('Такая подписка уже есть')
        if self.user == self.author:
            raise ValidationError('Нельзя подписаться на самого себя')
        return super().clean()

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
