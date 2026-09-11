from django.db import models
from django.core.exceptions import ObjectDoesNotExist

class Person(models.Model):
    objects = models.Manager()
    DoesNotExist = ObjectDoesNotExist
    name = models.CharField(max_length=100)
    acquaintances = models.ManyToManyField(
        'self', through='Relationship', symmetrical=False,
        related_name='known_by'
    )
    def __str__(self):
        return self.name

class Relationship(models.Model):
    objects = models.Manager()
    from_person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='outgoing_rel')
    to_person   = models.ForeignKey(Person, on_delete=models.CASCADE, related_name='incoming_rel')
    since_date  = models.DateField(null=True, blank=True)
    group       = models.CharField(
        max_length=50,
        choices=[('familia', 'Familia'), ('amigos', 'Amigos'), ('trabajo', 'Trabajo')],
        default='amigos'
    )

    class Meta:
        unique_together = ('from_person', 'to_person')

    def __str__(self):
        return f"{self.from_person}→{self.to_person} ({self.group})"