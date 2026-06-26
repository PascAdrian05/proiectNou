from typing import Literal


class PlanLimits:
    """Configuration for subscription plan limits."""
    
    # Plan types
    FREE: str = "free"
    BASIC: str = "basic"
    PRO: str = "pro"
    
    # Website limits
    WEBSITE_LIMITS = {
        FREE: 3,
        BASIC: 10,
        PRO: float('inf')  # Unlimited
    }
    
    # Scan frequency limits (in hours)
    SCAN_FREQUENCY_LIMITS = {
        FREE: 168,  # Weekly (7 days * 24 hours)
        BASIC: 24,  # Daily
        PRO: 1,    # Hourly
    }
    
    # Daily scan count limits
    DAILY_SCAN_LIMITS = {
        FREE: 5,    # 5 scans per day for free
        BASIC: 50,  # 50 scans per day for basic
        PRO: float('inf'),  # Unlimited for pro
    }
    
    # Feature availability
    FEATURES = {
        FREE: {
            "ai_insights": False,
            "behavior_risk_scoring": False,
            "custom_branding": False,
            "pdf_exports": False,
            "shareable_reports": False,
            "priority_alerts": False,
            "api_access": False,
        },
        BASIC: {
            "ai_insights": True,
            "behavior_risk_scoring": False,
            "custom_branding": False,
            "pdf_exports": True,
            "shareable_reports": True,
            "priority_alerts": True,
            "api_access": False,
        },
        PRO: {
            "ai_insights": True,
            "behavior_risk_scoring": True,
            "custom_branding": True,
            "pdf_exports": True,
            "shareable_reports": True,
            "priority_alerts": True,
            "api_access": True,
        },
    }
    
    @classmethod
    def get_website_limit(cls, plan: str) -> int:
        """Get maximum number of websites for a plan."""
        return cls.WEBSITE_LIMITS.get(plan, cls.WEBSITE_LIMITS[cls.FREE])
    
    @classmethod
    def get_scan_frequency_limit(cls, plan: str) -> int:
        """Get minimum scan interval (in hours) for a plan."""
        return cls.SCAN_FREQUENCY_LIMITS.get(plan, cls.SCAN_FREQUENCY_LIMITS[cls.FREE])
    
    @classmethod
    def has_feature(cls, plan: str, feature: str) -> bool:
        """Check if a plan has access to a specific feature."""
        plan_features = cls.FEATURES.get(plan, cls.FEATURES[cls.FREE])
        return plan_features.get(feature, False)
    
    @classmethod
    def can_add_website(cls, plan: str, current_count: int) -> tuple[bool, str]:
        """Check if a plan can add more websites."""
        limit = cls.get_website_limit(plan)
        if limit == float('inf'):
            return True, ""
        if current_count >= limit:
            return False, f"Your {plan} plan allows maximum {limit} websites"
        return True, ""
    
    @classmethod
    def can_scan(cls, plan: str, last_scan_hours_ago: int) -> tuple[bool, str]:
        """Check if a plan can perform a scan based on frequency limits."""
        min_interval = cls.get_scan_frequency_limit(plan)
        if last_scan_hours_ago < min_interval:
            return False, f"Your {plan} plan allows scans every {min_interval} hours"
        return True, ""
    
    @classmethod
    def get_daily_scan_limit(cls, plan: str) -> int:
        """Get maximum number of scans per day for a plan."""
        return cls.DAILY_SCAN_LIMITS.get(plan, cls.DAILY_SCAN_LIMITS[cls.FREE])
    
    @classmethod
    def can_scan_by_count(cls, plan: str, scans_used: int, scans_limit: int) -> tuple[bool, str]:
        """Check if a plan can perform a scan based on daily count limits."""
        limit = cls.get_daily_scan_limit(plan)
        if limit == float('inf'):
            return True, ""
        if scans_used >= limit:
            return False, f"Daily scan limit reached ({scans_used}/{limit}). Limit resets in 24 hours."
        return True, ""
