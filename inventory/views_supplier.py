"""
Supplier Dashboard Views
"""
from rest_framework import views, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.utils import timezone

from inventory.models import Supplier, PurchaseOrder
from inventory.serializers import PurchaseOrderSerializer
from inventory.services.supplier_service import SupplierService


class SupplierDashboardView(views.APIView):
    """GET /api/suppliers/{id}/dashboard/"""
    permission_classes = [permissions.AllowAny]

    
    def get(self, request, supplier_id):
        try:
            summary = SupplierService.get_supplier_summary(supplier_id)
            
            if not summary:
                return Response(
                    {'error': 'Supplier not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            recent_orders = PurchaseOrder.objects.filter(
                supplier_id=supplier_id
            ).order_by('-created_at')[:10]
            
            suggestions = SupplierService.generate_supplier_purchase_suggestions(supplier_id)
            
            dashboard_data = {
                'summary': {
                    'supplier': summary['supplier'],
                    'ingredients_count': summary['ingredients_count'],
                    'total_weekly_demand': round(summary['total_weekly_demand'], 2),
                    'low_stock_alerts': summary['low_stock_alerts'],
                    'pending_orders': summary['pending_orders']
                },
                'ingredients': summary['active_ingredients'],
                'recent_orders': PurchaseOrderSerializer(recent_orders, many=True).data,
                'purchase_suggestions': suggestions['suggestions'] if suggestions else [],
                'timestamp': timezone.now().isoformat()
            }
            
            return Response(dashboard_data)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SupplierForecastView(views.APIView):
    """GET /api/suppliers/{id}/forecast/"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, supplier_id):
        try:
            days = int(request.query_params.get('days', 14))
            forecast_data = SupplierService.get_supplier_demand_forecast(supplier_id, days)
            
            if not forecast_data:
                return Response(
                    {'error': 'Supplier not found or no forecast data'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(forecast_data)
            
        except ValueError:
            return Response(
                {'error': 'Invalid days parameter'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SupplierPurchaseSuggestionsView(views.APIView):
    """GET/POST /api/suppliers/{id}/suggest-purchase/"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, supplier_id):
        try:
            suggestions = SupplierService.generate_supplier_purchase_suggestions(supplier_id)
            
            if not suggestions:
                return Response(
                    {'error': 'Supplier not found or no suggestions'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(suggestions)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def post(self, request, supplier_id):
        try:
            from inventory.services.smart_po import generate_smart_po
            
            selected_suggestions = request.data.get('suggestions', [])
            created_by = request.user
            created_orders = []
            
            for suggestion in selected_suggestions:
                from inventory.models import Store, Ingredient
                
                try:
                    store = Store.objects.get(id=suggestion['store']['id'])
                    ingredient = Ingredient.objects.get(id=suggestion['ingredient']['id'])
                    
                    po = generate_smart_po(
                        store=store,
                        ingredient=ingredient,
                        created_by=created_by,
                        days=7
                    )
                    
                    if po:
                        created_orders.append({
                            'po_id': po.id,
                            'ingredient': ingredient.name,
                            'quantity': suggestion['suggested_order'],
                            'store': store.name
                        })
                        
                except (Store.DoesNotExist, Ingredient.DoesNotExist):
                    continue
            
            return Response({
                'message': f'Created {len(created_orders)} purchase orders',
                'created_orders': created_orders
            })
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SupplierPerformanceView(views.APIView):
    """GET /api/suppliers/{id}/performance/"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, supplier_id):
        try:
            performance = SupplierService.get_supplier_performance(supplier_id)
            
            if not performance:
                return Response(
                    {'error': 'Supplier not found'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response(performance)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def supplier_low_stock_alerts(request, supplier_id):
    """GET /api/suppliers/{id}/low-stock-alerts/"""
    try:
        summary = SupplierService.get_supplier_summary(supplier_id)
        
        if not summary:
            return Response(
                {'error': 'Supplier not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        low_stock_alerts = []
        
        for ingredient in summary['active_ingredients']:
            for store_data in ingredient['weekly_demand_by_store']:
                if store_data['is_low_stock']:
                    alert = {
                        'ingredient': {
                            'id': ingredient['id'],
                            'name': ingredient['name'],
                            'sku': ingredient['sku'],
                            'unit': ingredient['unit']
                        },
                        'store': {
                            'id': store_data['store_id'],
                            'name': store_data['store_name']
                        },
                        'current_stock': store_data['current_stock'],
                        'weekly_demand': store_data['weekly_demand'],
                        'days_of_supply': store_data['days_of_supply'],
                        'alert_level': 'CRITICAL' if store_data['days_of_supply'] < 3 else 'WARNING'
                    }
                    low_stock_alerts.append(alert)
        
        low_stock_alerts.sort(key=lambda x: (
            0 if x['alert_level'] == 'CRITICAL' else 1,
            x['days_of_supply']
        ))
        
        return Response({
            'supplier_id': supplier_id,
            'supplier_name': summary['supplier']['name'],
            'total_alerts': len(low_stock_alerts),
            'critical_alerts': len([a for a in low_stock_alerts if a['alert_level'] == 'CRITICAL']),
            'alerts': low_stock_alerts[:20]
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )