from django.db import models

class Ingredient(models.Model):
    name = models.CharField(max_length=255)
    unit = models.CharField(max_length=20)
    current_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    def __str__(self):
        return self.name


class IngredientPriceHistory(models.Model):
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE, related_name='history')
    date = models.DateField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    season = models.CharField(max_length=100, blank=True)
    demand_level = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ingredient.name} - {self.date}"
