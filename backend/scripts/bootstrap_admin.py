from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import Tenant, User, UserRole
from app.db.session import SessionLocal


def main() -> None:
    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == settings.BOOTSTRAP_TENANT_SLUG))
        if tenant is None:
            tenant = Tenant(slug=settings.BOOTSTRAP_TENANT_SLUG, name=settings.BOOTSTRAP_TENANT_NAME)
            db.add(tenant)
            db.flush()
        user = db.scalar(
            select(User).where(User.tenant_id == tenant.id, User.email == settings.BOOTSTRAP_ADMIN_EMAIL.lower())
        )
        if user is None:
            user = User(
                tenant_id=tenant.id,
                email=settings.BOOTSTRAP_ADMIN_EMAIL.lower(),
                full_name="Administrator",
                hashed_password=hash_password(settings.BOOTSTRAP_ADMIN_PASSWORD),
                role=UserRole.admin,
            )
            db.add(user)
            action = "created"
        else:
            user.hashed_password = hash_password(settings.BOOTSTRAP_ADMIN_PASSWORD)
            user.role = UserRole.admin
            user.is_active = True
            action = "updated"
        db.commit()
        print(f"Admin {action}: {user.email} in tenant {tenant.slug}")


if __name__ == "__main__":
    main()
