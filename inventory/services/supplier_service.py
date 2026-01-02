"""
Supplier Service for Dashboard
"""
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta
from inventory.models import (
    Supplier, Ingredient, Store, InventoryRecord,
    PurchaseOrder, Forecast, Sale, RecipeComponent,
    PurchaseOrderItem, MessageLog
)
from inventory.services.stock import get_current_stock
from inventory.services.forecast import get_forecast_demand


class SupplierService:
    """Service for supplier dashboard and analytics"""
    
    @staticmethod
    def get_supplier_summary(supplier_id):
        """Get high-level summary for supplier dashboard"""
        try:
            supplier = Supplier.objects.get(id=supplier_id)
            
            ingredients = Ingredient.objects.filter(default_supplier=supplier)
            
            summary = {
                'supplier': {
                    'id': supplier.id,
                    'name': supplier.name,
                    'contact': supplier.contact_person,
                    'phone': supplier.phone,
                    'email': supplier.email
                },
                'ingredients_count': ingredients.count(),
                'active_ingredients': [],
                'total_weekly_demand': 0,
                'low_stock_alerts': 0,
                'pending_orders': 0
            }
            
            for ingredient in ingredients:
                stores = Store.objects.filter(
                    inventory_records__ingredient=ingredient
                ).distinct()
                
                ingredient_data = {
                    'id': ingredient.id,
                    'name': ingredient.name,
                    'sku': ingredient.sku,
                    'unit': ingredient.unit_of_measure,
                    'stores_count': stores.count(),
                    'weekly_demand_by_store': [],
                    'total_weekly_demand': 0,
                    'low_stock_stores': 0
                }
                
                for store in stores:
                    forecast_demand = get_forecast_demand(store, ingredient, days=7)
                    current_stock = get_current_stock(store, ingredient)
                    is_low_stock = current_stock < (forecast_demand * 0.3)
                    
                    store_data = {
                        'store_id': store.id,
                        'store_name': store.name,
                        'weekly_demand': round(forecast_demand, 2),
                        'current_stock': round(current_stock, 2),
                        'is_low_stock': is_low_stock,
                        'days_of_supply': round(current_stock / (forecast_demand / 7), 1) if forecast_demand > 0 else 999
                    }
                    
                    ingredient_data['weekly_demand_by_store'].append(store_data)
                    ingredient_data['total_weekly_demand'] += forecast_demand
                    
                    if is_low_stock:
                        ingredient_data['low_stock_stores'] += 1
                        summary['low_stock_alerts'] += 1
                
                summary['total_weekly_demand'] += ingredient_data['total_weekly_demand']
                summary['active_ingredients'].append(ingredient_data)
            
            summary['pending_orders'] = PurchaseOrder.objects.filter(
                supplier=supplier,
                status__in=['DRAFT', 'SENT', 'CONFIRMED']
            ).count()
            
            return summary
            
        except Supplier.DoesNotExist:
            return None
    
    @staticmethod
    def get_supplier_demand_forecast(supplier_id, days=14):
        """Get aggregated demand forecast"""
        try:
            supplier = Supplier.objects.get(id=supplier_id)
            ingredients = Ingredient.objects.filter(default_supplier=supplier)
            
            forecast_data = []
            today = timezone.now().date()
            end_date = today + timedelta(days=days)
            
            for ingredient in ingredients:
                stores = Store.objects.filter(
                    inventory_records__ingredient=ingredient
                ).distinct()
                
                total_forecast = Forecast.objects.filter(
                    ingredient=ingredient,
                    store__in=stores,
                    forecast_date__gte=today,
                    forecast_date__lt=end_date
                ).aggregate(total=Sum('forecast_quantity'))['total'] or 0
                
                if total_forecast > 0:
                    forecast_data.append({
                        'ingredient': {
                            'id': ingredient.id,
                            'name': ingredient.name,
                            'unit': ingredient.unit_of_measure
                        },
                        'total_demand': round(total_forecast, 2),
                        'stores_count': stores.count(),
                        'daily_average': round(total_forecast / days, 2)
                    })
            
            return {
                'supplier_id': supplier_id,
                'supplier_name': supplier.name,
                'forecast_period': f"{today} to {end_date}",
                'total_days': days,
                'ingredients': forecast_data,
                'total_demand': sum(item['total_demand'] for item in forecast_data)
            }
            
        except Supplier.DoesNotExist:
            return None
    
    @staticmethod
    def generate_supplier_purchase_suggestions(supplier_id):
        """Generate purchase suggestions"""
        try:
            supplier = Supplier.objects.get(id=supplier_id)
            ingredients = Ingredient.objects.filter(default_supplier=supplier)
            
            suggestions = []
            
            for ingredient in ingredients:
                stores = Store.objects.filter(
                    inventory_records__ingredient=ingredient
                ).distinct()
                
                for store in stores:
                    stock = get_current_stock(store, ingredient)
                    demand = get_forecast_demand(store, ingredient, days=7)
                    reorder_point = demand
                    
                    if stock < reorder_point:
                        order_qty = max(0, (demand - stock) * 1.2)
                        
                        if ingredient.target_stock_level:
                            order_qty = max(order_qty, ingredient.target_stock_level - stock)
                        
                        if order_qty > 0:
                            suggestions.append({
                                'store': {'id': store.id, 'name': store.name},
                                'ingredient': {
                                    'id': ingredient.id,
                                    'name': ingredient.name,
                                    'sku': ingredient.sku,
                                    'unit': ingredient.unit_of_measure
                                },
                                'current_stock': round(stock, 2),
                                'weekly_demand': round(demand, 2),
                                'suggested_order': round(order_qty, 2),
                                'urgency': 'HIGH' if stock < (demand * 0.2) else 'MEDIUM',
                                'days_of_supply': round(stock / (demand / 7), 1) if demand > 0 else 999
                            })
            
            suggestions.sort(key=lambda x: (0 if x['urgency'] == 'HIGH' else 1, x['days_of_supply']))
            
            return {
                'supplier_id': supplier_id,
                'supplier_name': supplier.name,
                'suggestions_count': len(suggestions),
                'suggestions': suggestions
            }
            
        except Supplier.DoesNotExist:
            return None
    
    @staticmethod
    def get_supplier_performance(supplier_id):
        """Calculate performance metrics"""
        try:
            supplier = Supplier.objects.get(id=supplier_id)
            
            total_orders = PurchaseOrder.objects.filter(supplier=supplier).count()
            completed_orders = PurchaseOrder.objects.filter(
                supplier=supplier,
                status='RECEIVED'
            ).count()
            
            completed_po_items = PurchaseOrder.objects.filter(
                supplier=supplier,
                status='RECEIVED'
            )
            
            on_time_orders = completed_po_items.filter(
                expected_delivery_date__isnull=False
            ).count()
            
            metrics = {
                'order_volume': {
                    'total': total_orders,
                    'completed': completed_orders,
                    'completion_rate': round((completed_orders / total_orders * 100), 2) if total_orders > 0 else 0
                },
                'delivery_performance': {
                    'on_time_rate': round((on_time_orders / completed_orders * 100), 2) if completed_orders > 0 else 0,
                    'avg_response_time': 'N/A'
                },
                'ingredient_coverage': {
                    'total_ingredients': Ingredient.objects.filter(default_supplier=supplier).count(),
                    'active_stores': Store.objects.filter(
                        inventory_records__ingredient__default_supplier=supplier
                    ).distinct().count()
                }
            }
            
            return {
                'supplier_id': supplier_id,
                'supplier_name': supplier.name,
                'metrics': metrics
            }
            
        except Supplier.DoesNotExist:
            return None