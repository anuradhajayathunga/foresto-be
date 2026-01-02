"""
Simple demo data for presentation
"""
import os
import django
import random
from datetime import datetime, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

from django.utils import timezone
from inventory.models import *

def create_demo_data():
    print("Creating demo data for PP1...")
    
    # Create admin user
    user, created = User.objects.get_or_create(
        username='admin',
        defaults={'email': 'admin@example.com'}
    )
    if created:
        user.set_password('admin123')
        user.is_staff = True
        user.is_superuser = True
        user.save()
        print("Created admin user")
    
    # Create 2 suppliers
    supplier1 = Supplier.objects.create(
        name="Colombo Fresh Produce",
        contact_person="Mr. Perera",
        phone="+94771234567",
        email="supplier1@example.com"
    )
    
    supplier2 = Supplier.objects.create(
        name="Western Province Meat Suppliers",
        contact_person="Mr. Fernando",
        phone="+94771234568",
        email="supplier2@example.com"
    )
    print("Created 2 suppliers")
    
    # Create 5 ingredients
    ingredients = []
    ingredient_data = [
        {"name": "Chicken Breast", "sku": "CHK001", "unit": "kg", "supplier": supplier2},
        {"name": "Rice", "sku": "RIC001", "unit": "kg", "supplier": supplier1},
        {"name": "Tomatoes", "sku": "TOM001", "unit": "kg", "supplier": supplier1},
        {"name": "Onions", "sku": "ONI001", "unit": "kg", "supplier": supplier1},
        {"name": "Coconut Milk", "sku": "COC001", "unit": "l", "supplier": supplier1},
    ]
    
    for data in ingredient_data:
        ingredient = Ingredient.objects.create(
            sku=data["sku"],
            name=data["name"],
            unit_of_measure=data["unit"],
            min_stock_level=10,
            target_stock_level=25,
            default_supplier=data["supplier"]
        )
        ingredients.append(ingredient)
    print("Created 5 ingredients")
    
    # Create 2 stores (restaurants)
    store1 = Store.objects.create(
        name="Colombo City Restaurant",
        address="123 Galle Road, Colombo",
        phone="+94761234567",
        owner_id=user
    )
    
    store2 = Store.objects.create(
        name="Kandy Hill View Cafe",
        address="456 Kandy Road, Kandy",
        phone="+94761234568",
        owner_id=user
    )
    print("Created 2 stores")
    
    # Create 3 menu items
    chicken_rice = MenuItem.objects.create(
        code="CHK_RICE",
        name="Chicken Rice",
        category="Rice",
        unit="plate"
    )
    
    veg_curry = MenuItem.objects.create(
        code="VEG_CURRY",
        name="Vegetable Curry",
        category="Curry",
        unit="plate"
    )
    
    kottu = MenuItem.objects.create(
        code="KOTTU",
        name="Kottu Roti",
        category="Roti",
        unit="plate"
    )
    print("Created 3 menu items")
    
    # Create recipe components
    RecipeComponent.objects.create(
        menu_item=chicken_rice,
        ingredient=ingredients[0],  # Chicken
        quantity_per_portion=0.2  # 200g per plate
    )
    RecipeComponent.objects.create(
        menu_item=chicken_rice,
        ingredient=ingredients[1],  # Rice
        quantity_per_portion=0.15  # 150g per plate
    )
    
    RecipeComponent.objects.create(
        menu_item=veg_curry,
        ingredient=ingredients[2],  # Tomatoes
        quantity_per_portion=0.1  # 100g per plate
    )
    RecipeComponent.objects.create(
        menu_item=veg_curry,
        ingredient=ingredients[3],  # Onions
        quantity_per_portion=0.05  # 50g per plate
    )
    print("Created recipe components")
    
    # Create inventory records
    for store in [store1, store2]:
        for ingredient in ingredients:
            InventoryRecord.objects.create(
                store=store,
                ingredient=ingredient,
                quantity_on_hand=random.uniform(5, 20)
            )
    print("Created inventory records")
    
    # Create sales data (last 7 days)
    today = timezone.now().date()
    for i in range(7):
        sale_date = today - timedelta(days=6-i)
        
        # Store 1 sales
        Sale.objects.create(
            store=store1,
            menu_item=chicken_rice,
            sale_date=sale_date,
            quantity_sold=random.randint(10, 30),
            source="MANUAL"
        )
        
        Sale.objects.create(
            store=store1,
            menu_item=veg_curry,
            sale_date=sale_date,
            quantity_sold=random.randint(5, 15),
            source="MANUAL"
        )
        
        # Store 2 sales
        Sale.objects.create(
            store=store2,
            menu_item=chicken_rice,
            sale_date=sale_date,
            quantity_sold=random.randint(8, 20),
            source="MANUAL"
        )
    print("Created sales data")
    
    # Create forecast data (next 7 days)
    for i in range(7):
        forecast_date = today + timedelta(days=i+1)
        
        for store in [store1, store2]:
            for ingredient in ingredients:
                Forecast.objects.create(
                    store=store,
                    ingredient=ingredient,
                    forecast_date=forecast_date,
                    forecast_quantity=random.uniform(5, 15),
                    model_name="ARIMA"
                )
    print("Created forecast data")
    
    # Create a purchase order
    po = PurchaseOrder.objects.create(
        store=store1,
        supplier=supplier1,
        created_by=user,
        status="CONFIRMED",
        expected_delivery_date=today + timedelta(days=3)
    )
    
    PurchaseOrderItem.objects.create(
        purchase_order=po,
        ingredient=ingredients[1],  # Rice
        ordered_quantity=50,
        unit_price=200
    )
    print("Created a purchase order")
    
    print("\n" + "="*50)
    print("✅ DEMO DATA CREATED SUCCESSFULLY!")
    print("="*50)
    print("\nYou can now:")
    print("1. Run server: python manage.py runserver")
    print("2. Login to admin: http://localhost:8000/admin/")
    print("   Username: admin, Password: admin123")
    print("3. Test API: http://localhost:8000/api/inventory/suppliers/1/dashboard/")
    print("\nFor PP1 presentation, show:")
    print("✓ Database schema (models.py)")
    print("✓ Django admin with data")
    print("✓ Supplier dashboard API response")
    print("✓ Smart PO generation")

if __name__ == "__main__":
    create_demo_data()