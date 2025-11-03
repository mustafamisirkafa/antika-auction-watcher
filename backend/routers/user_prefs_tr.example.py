"""
Example of Turkish-localized User Preferences API (Phase 16-TR)
This shows key changes needed in user_prefs.py
"""

# Add at the top of the file:
from backend.core.i18n import tr_error, tr_success, tr_message

# Example 1: Update error responses
@router.get("", response_model=UserPreferencesResponse)
async def get_user_preferences(...):
    if not user_id or not team_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=tr_error("validation_error")  # "Ge?ersiz veri giri?i"
        )
    
    try:
        prefs = await service.get_user_preferences(user_id, team_id)
        if not prefs:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=tr_error("not_found")  # "Kaynak bulunamad?"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=tr_error("server_error")  # "Sunucu hatas? olu?tu"
        )

# Example 2: Update success responses
@router.post("/update", response_model=UpdatePreferenceResponse)
async def update_user_preference(request: UpdatePreferenceRequest, ...):
    # Validate action
    if request.action not in valid_actions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=tr_error("invalid_action")  # "Ge?ersiz i?lem"
        )
    
    result = await service.update_user_preference(...)
    
    # Return response with Turkish message
    message_key_map = {
        "add_allow": "seller_added_allowlist",      # "Sat?c? izin listesine eklendi"
        "remove_allow": "seller_removed_allowlist",  # "Sat?c? izin listesinden kald?r?ld?"
        "add_block": "seller_added_blocklist",      # "Sat?c? engel listesine eklendi"
        "remove_block": "seller_removed_blocklist"  # "Sat?c? engel listesinden kald?r?ld?"
    }
    
    return UpdatePreferenceResponse(
        success=True,
        message=tr_success(message_key_map[request.action]),  # Turkish message
        affected_list=result["list_type"],
        seller_id=request.seller_id,
        new_total=result["new_total"],
        updated_at=result["updated_at"]
    )

# Example 3: Check endpoint with Turkish responses
@router.get("/check/{seller_id}")
async def check_seller_allowed(...):
    try:
        result = await service.check_seller_allowed(...)
        return {
            "allowed": result["allowed"],
            "reason": tr_message(result["reason_key"])  # Translate reason
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=tr_error("server_error")
        )
