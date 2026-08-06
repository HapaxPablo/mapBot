from django.contrib.auth.models import User
from django.db import models


class PointVote(models.Model):
    class VoteType(models.TextChoices):
        LIKE = 'like', 'Лайк'
        DISLIKE = 'dislike', 'Дизлайк'

    point = models.ForeignKey('points.Point', on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_votes')
    vote_type = models.CharField(max_length=7, choices=VoteType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('point', 'user'), name='unique_point_vote_per_user'),
        ]

    def __str__(self):
        return f'{self.user_id}: {self.point_id} ({self.vote_type})'
