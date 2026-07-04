from django.db import models

class ShortDramaForyou(models.Model):
    title = models.CharField(max_length=200)
    dramas = models.ManyToManyField("ShortDrama",blank=True,related_name="foryou_categories")
    order_by = models.IntegerField(default=0)
    last_update = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order_by"]

    def __str__(self):
        return self.title


class ShortDrama(models.Model):
    subject_id = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=500)
    slug = models.SlugField(max_length=500, unique=True)
    cover= models.JSONField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)
    total_episodes = models.PositiveIntegerField(default=0)
    total_views = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

class ShortDramaEpisode(models.Model):
    drama = models.ForeignKey(ShortDrama, on_delete=models.CASCADE, related_name="episodes")
    mini_id = models.CharField(max_length=100, unique=True)
    subject_id = models.CharField(max_length=100)
    season = models.PositiveIntegerField(default=1)
    episode_number = models.PositiveIntegerField()
    play_url = models.URLField(max_length=2000)
    thumbnail = models.URLField(blank=True, null=True)
    duration = models.PositiveIntegerField(blank=True,null=True,help_text="Duration in seconds")
    width = models.PositiveIntegerField(blank=True, null=True)
    height = models.PositiveIntegerField(blank=True, null=True)
    file_size = models.BigIntegerField(blank=True, null=True)
    lock_status = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["episode_number"]
        unique_together = ("drama", "episode_number")

    def __str__(self):
        return f"{self.drama.title} - Episode {self.episode_number}"