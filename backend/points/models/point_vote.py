"""Компонент серверной части GeoMap."""

from django.contrib.auth.models import User
from django.db import models


class PointVote(models.Model):
    """Класс, инкапсулирующий логику серверного компонента GeoMap."""
    class VoteType(models.TextChoices):
        """Класс, инкапсулирующий логику серверного компонента GeoMap."""
        LIKE = 'like', 'Лайк'
        DISLIKE = 'dislike', 'Дизлайк'

    point = models.ForeignKey('points.Point', on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='point_votes')
    vote_type = models.CharField(max_length=7, choices=VoteType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Класс, инкапсулирующий логику серверного компонента GeoMap."""
        constraints = [
            models.UniqueConstraint(fields=('point', 'user'), name='unique_point_vote_per_user'),
        ]

    def __str__(self):
        """Выполняет операцию серверного компонента GeoMap."""
        return f'{self.user_id}: {self.point_id} ({self.vote_type})'
