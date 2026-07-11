from django.core.cache import cache
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from api.models import ShortDrama, ShortDramaForyou

class CachingTests(APITestCase):
    def setUp(self):
        # Clear cache before tests
        cache.clear()
        
        # Create a user and token for authentication
        self.user = User.objects.create_user(username="testuser", password="password")
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        
        # Create sample ShortDrama
        self.drama = ShortDrama.objects.create(
            subject_id="sub_1",
            title="Test Drama",
            slug="test-drama",
            is_active=True,
            is_everyone_search=True
        )
        
        self.category = ShortDramaForyou.objects.create(
            title="For You Category",
            order_by=1,
            is_active=True
        )
        self.category.dramas.add(self.drama)

    def tearDown(self):
        cache.clear()

    def test_all_short_dramas_cached(self):
        url = "/api/short-drama/"
        # First request (uncached)
        response1 = self.client.get(url)
        self.assertEqual(response1.status_code, 200)
        
        # Check cache contains the data
        cache_key = "all_short_dramas_"
        self.assertIsNotNone(cache.get(cache_key))
        
        # Modify the drama name in DB directly
        self.drama.title = "Modified Title"
        self.drama.save()
        
        # Second request (cached, should return old title "Test Drama")
        response2 = self.client.get(url)
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.json()['results'][0]['title'], "Test Drama")

    def test_short_drama_by_id_cached(self):
        url = f"/api/short-drama/detail/?id={self.drama.id}"
        response1 = self.client.get(url)
        self.assertEqual(response1.status_code, 200)
        
        # Check cache
        cache_key = f"short_drama_id_{self.drama.id}"
        self.assertIsNotNone(cache.get(cache_key))
        
        # Modify title
        self.drama.title = "Modified ID"
        self.drama.save()
        
        # Fetch again
        response2 = self.client.get(url)
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.json()['data']['title'], "Test Drama")

    def test_everyone_watching_not_cached(self):
        url = "/api/short-drama/everyone/"
        response1 = self.client.get(url)
        self.assertEqual(response1.status_code, 200)
        
        # Modify title in DB
        self.drama.title = "Modified Everyone"
        self.drama.save()
        
        # Fetch again (should be uncached, returning Modified Everyone)
        response2 = self.client.get(url)
        self.assertEqual(response2.status_code, 200)
        self.assertEqual(response2.json()['data'][0]['title'], "Modified Everyone")

    def test_unauthenticated_request_rejected(self):
        url = f"/api/short-drama/detail/?id={self.drama.id}"
        
        # Populate the cache first with authenticated request
        response1 = self.client.get(url)
        self.assertEqual(response1.status_code, 200)
        
        # Clear credentials (unauthenticated)
        self.client.credentials()
        
        # Request should fail with 401 Unauthorized, despite being in cache
        response2 = self.client.get(url)
        self.assertEqual(response2.status_code, 401)


