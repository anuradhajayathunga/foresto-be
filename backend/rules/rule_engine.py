def apply_rules(
    base_prediction,
    is_festival,
    festival_type,
    is_poya_day,
    is_heavy_rain,
    is_weekend
):
    """
    Applies rule-based adjustment factors on top of ML prediction.
    
    Parameters:
    - base_prediction (float): ML model output
    - is_festival (int): 1 if festival day else 0
    - festival_type (str): Festival name
    - is_poya_day (int): 1 if poya day
    - is_heavy_rain (int): 1 if heavy rain
    - is_weekend (int): 1 if weekend
    
    Returns:
    - adjusted_prediction (float)
    """

    adjustment_factor = 1.0

    # Major festivals
    if is_festival:
        if festival_type == "Sinhala_Tamil_New_Year":
            adjustment_factor *= 1.8
        elif festival_type == "Vesak":
            adjustment_factor *= 1.4

    # Poya day effect
    if is_poya_day:
        adjustment_factor *= 0.85

    # Weather effect
    if is_heavy_rain:
        adjustment_factor *= 0.9

    # Weekend effect
    if is_weekend:
        adjustment_factor *= 1.2

    adjusted_prediction = base_prediction * adjustment_factor
    return round(adjusted_prediction, 2)
