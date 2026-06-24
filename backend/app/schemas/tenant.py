from pydantic import BaseModel, EmailStr, HttpUrl


class TenantSettingsUpdate(BaseModel):
    alert_email: EmailStr | None = None
    alert_webhook_url: HttpUrl | None = None
    brand_name: str | None = None
    brand_logo_url: HttpUrl | None = None
    report_primary_color: str | None = None
    report_base_url: HttpUrl | None = None
    report_cta_text: str | None = None
    report_cta_url: HttpUrl | None = None


class TenantSettingsRead(BaseModel):
    name: str
    alert_email: EmailStr | None = None
    alert_webhook_url: HttpUrl | None = None
    brand_name: str | None = None
    brand_logo_url: HttpUrl | None = None
    report_primary_color: str | None = None
    report_base_url: HttpUrl | None = None
    report_cta_text: str | None = None
    report_cta_url: HttpUrl | None = None
