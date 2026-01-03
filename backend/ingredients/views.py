from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

# UI 1: Predict ingredient price
@api_view(['POST'])
def predict_price(request):
    # Inputs: ingredient, quantity, date (month ok)
    ingredient = request.data.get('ingredient')
    quantity = float(request.data.get('quantity', 0))
    date = request.data.get('date')

    # Dummy ML stub — replace with your model call
    base_price = 100.0
    trend_factor = 1.05  # pretend slight increase
    predicted = round(base_price * trend_factor * (quantity if quantity else 1), 2)

    return Response({'predicted_price': predicted}, status=status.HTTP_200_OK)

# UI 2: Prediction result & supplier recommendation
@api_view(['POST'])
def prediction_result_with_suppliers(request):
    # Input: ingredient, quantity, date
    # Compute prediction as above
    predicted = 120.0
    trend = 'up'  # or 'down'
    confidence = 78  # percent

    suppliers = [
        {'name': 'Supplier A', 'reliability': 82, 'fairness': 88, 'label': 'Best Choice'},
        {'name': 'Supplier B', 'reliability': 70, 'fairness': 75, 'label': 'Acceptable'},
        {'name': 'Supplier C', 'reliability': 55, 'fairness': 60, 'label': 'Not Recommended'},
    ]
    return Response({
        'predicted_price': predicted,
        'trend': trend,
        'confidence': confidence,
        'suppliers': suppliers
    }, status=status.HTTP_200_OK)

# UI 3: Supplier price data entry
@api_view(['POST'])
def supplier_price_entry(request):
    supplier = request.data.get('supplier')
    ingredient = request.data.get('ingredient')
    price = request.data.get('price')
    date = request.data.get('date')

    # Store internally: for now, append to a log/placeholder.
    # Replace this with a proper SupplierPrice model later.
    # Example: SupplierPrice.objects.create(...)
    return Response({'status': 'stored'}, status=status.HTTP_201_CREATED)

# UI 4: Menu price calculator
@api_view(['POST'])
def menu_calculator(request):
    dish = request.data.get('dish')
    ingredients = request.data.get('ingredients', [])  # [{name, qty}]
    prep_cost = float(request.data.get('prepCost') or 0)
    margin = float(request.data.get('margin') or 0)

    # Stub predicted cost per ingredient (replace with your ML)
    per_item = []
    total_ingredient_cost = 0.0
    for item in ingredients:
        qty = float(item.get('qty') or 0)
        predicted_cost = round(50.0 * qty, 2)
        per_item.append({'name': item.get('name'), 'qty': qty, 'predicted_cost': predicted_cost})
        total_ingredient_cost += predicted_cost

    total_cost = round(total_ingredient_cost + prep_cost, 2)
    selling_price = round(total_cost * (1 + margin / 100), 2)
    profit = round(selling_price - total_cost, 2)

    return Response({
        'items': per_item,
        'total_ingredient_cost': round(total_ingredient_cost, 2),
        'total_cost': total_cost,
        'selling_price': selling_price,
        'profit': profit
    }, status=status.HTTP_200_OK)