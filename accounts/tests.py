from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import RestaurantMembership, Role

User = get_user_model()


class RegistrationAndMembershipTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        for name, label in Role.Names.choices:
            Role.objects.get_or_create(name=name, defaults={"description": label})

    def test_register_creates_restaurant_and_owner_membership(self):
        url = "/api/auth/register/"
        payload = {
            "username": "owner1",
            "email": "owner1@example.com",
            "password": "Str0ngPass!123",
            "password2": "Str0ngPass!123",
            "first_name": "Owner",
            "last_name": "One",
            "restaurant_name": "Sunrise Diner",
        }

        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(email="owner1@example.com")
        membership = RestaurantMembership.objects.select_related("restaurant", "role").get(user=user)

        self.assertEqual(membership.role.name, Role.Names.OWNER)
        self.assertEqual(membership.restaurant.name, "Sunrise Diner")
        self.assertTrue(membership.is_active)

    def test_owner_can_add_member_but_manager_cannot_manage_members(self):
        owner = User.objects.create_user(username="owner", email="owner@example.com", password="x")
        manager = User.objects.create_user(username="manager", email="manager@example.com", password="x")
        staff_user = User.objects.create_user(username="staff1", email="staff1@example.com", password="x")

        owner_role = Role.objects.get(name=Role.Names.OWNER)
        manager_role = Role.objects.get(name=Role.Names.MANAGER)

        # Create restaurant via owner signup-like flow
        from .models import Restaurant

        restaurant = Restaurant.objects.create(name="Test Rest")
        RestaurantMembership.objects.create(
            restaurant=restaurant,
            user=owner,
            role=owner_role,
            is_active=True,
        )
        RestaurantMembership.objects.create(
            restaurant=restaurant,
            user=manager,
            role=manager_role,
            is_active=True,
        )

        # Owner can invite staff
        self.client.force_authenticate(user=owner)
        add_url = f"/api/auth/restaurants/{restaurant.id}/members/"
        resp = self.client.post(
            add_url,
            {"user_id": staff_user.id, "role": Role.Names.STAFF},
            format="json",
            HTTP_X_RESTAURANT_ID=str(restaurant.id),
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        # Manager cannot manage members
        self.client.force_authenticate(user=manager)
        resp2 = self.client.post(
            add_url,
            {"user_id": staff_user.id, "role": Role.Names.VIEWER},
            format="json",
            HTTP_X_RESTAURANT_ID=str(restaurant.id),
        )
        self.assertEqual(resp2.status_code, status.HTTP_403_FORBIDDEN)

        
