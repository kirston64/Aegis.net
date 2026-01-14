"""
Aegis.net — Attack Mode Router
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta

from api.models import (
    AttackModeRequest,
    AttackModeResponse,
    ProtectionLevel,
    APIResponse
)

router = APIRouter()

# In-memory attack mode state
attack_mode_state: dict = {}


@router.post("/{domain}", response_model=AttackModeResponse)
async def activate_attack_mode(domain: str, request: AttackModeRequest):
    """
    Activate Under Attack Mode for a domain.
    
    This immediately raises the protection level and applies stricter
    filtering rules to mitigate an ongoing attack.
    
    - **level**: Protection level (0-4)
    - **duration_minutes**: How long to maintain this level
    - **reason**: Optional description of the attack
    """
    domain = domain.lower()
    now = datetime.utcnow()
    
    previous_level = attack_mode_state.get(domain, {}).get("level", ProtectionLevel.OBSERVE)
    
    attack_mode_state[domain] = {
        "level": request.level,
        "activated_at": now,
        "expires_at": now + timedelta(minutes=request.duration_minutes),
        "reason": request.reason
    }
    
    # TODO: Push to edge nodes
    
    return AttackModeResponse(
        domain=domain,
        level=request.level,
        previous_level=previous_level,
        activated_at=now,
        expires_at=now + timedelta(minutes=request.duration_minutes),
        auto_decrease=True
    )


@router.get("/{domain}", response_model=AttackModeResponse)
async def get_attack_mode_status(domain: str):
    """
    Get current attack mode status for a domain.
    """
    domain = domain.lower()
    
    if domain not in attack_mode_state:
        raise HTTPException(
            status_code=404,
            detail=f"No attack mode active for {domain}"
        )
    
    state = attack_mode_state[domain]
    
    return AttackModeResponse(
        domain=domain,
        level=state["level"],
        previous_level=ProtectionLevel.OBSERVE,
        activated_at=state["activated_at"],
        expires_at=state["expires_at"],
        auto_decrease=True
    )


@router.delete("/{domain}", response_model=APIResponse)
async def deactivate_attack_mode(domain: str):
    """
    Deactivate attack mode and return to normal protection level.
    """
    domain = domain.lower()
    
    if domain in attack_mode_state:
        del attack_mode_state[domain]
    
    return APIResponse(
        success=True,
        message=f"Attack mode deactivated for {domain}"
    )


@router.post("/{domain}/increase", response_model=AttackModeResponse)
async def increase_protection_level(domain: str):
    """
    Quickly increase protection level by one step.
    """
    domain = domain.lower()
    now = datetime.utcnow()
    
    current_level = attack_mode_state.get(domain, {}).get("level", ProtectionLevel.OBSERVE)
    new_level = min(current_level + 1, ProtectionLevel.LOCKDOWN)
    
    attack_mode_state[domain] = {
        "level": new_level,
        "activated_at": now,
        "expires_at": now + timedelta(minutes=60),
        "reason": "Manual increase"
    }
    
    return AttackModeResponse(
        domain=domain,
        level=new_level,
        previous_level=current_level,
        activated_at=now,
        expires_at=now + timedelta(minutes=60),
        auto_decrease=True
    )


@router.post("/{domain}/decrease", response_model=AttackModeResponse)
async def decrease_protection_level(domain: str):
    """
    Decrease protection level by one step.
    """
    domain = domain.lower()
    now = datetime.utcnow()
    
    current_level = attack_mode_state.get(domain, {}).get("level", ProtectionLevel.OBSERVE)
    new_level = max(current_level - 1, ProtectionLevel.OBSERVE)
    
    if new_level == ProtectionLevel.OBSERVE:
        # Full deactivation
        if domain in attack_mode_state:
            del attack_mode_state[domain]
    else:
        attack_mode_state[domain] = {
            "level": new_level,
            "activated_at": now,
            "expires_at": now + timedelta(minutes=60),
            "reason": "Manual decrease"
        }
    
    return AttackModeResponse(
        domain=domain,
        level=new_level,
        previous_level=current_level,
        activated_at=now,
        expires_at=now + timedelta(minutes=60),
        auto_decrease=True
    )
