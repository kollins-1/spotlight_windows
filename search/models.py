from django.db import models

class File(models.Model):
    name = models.CharField(max_length=255)           # File name
    path = models.CharField(max_length=500, unique=True)  # File path (unique for each file)
    content = models.TextField(blank=True)            # File content (optional, for searchable content)
    last_modified = models.DateTimeField()            # Last modified date

    def __str__(self):
        return self.name