# src/db/initial_data.py
from .models import Role, RoleEnum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import insert, select


async def initialize_roles(session):
    """Create default roles if they don't exist"""
    existing_roles = await session.execute(select(Role))
    existing_role_names = {role.name for role in existing_roles.scalars()}
    
    for role_enum in RoleEnum:
        if role_enum not in existing_role_names:
            session.add(Role(
                name=role_enum,
                description=f"System {role_enum.value} role",
                is_default=(role_enum == RoleEnum.STUDENT)
            ))
    
    await session.commit()