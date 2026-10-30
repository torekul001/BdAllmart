"""Optional workspace shell for existing Customer/Designer views; no business logic forks."""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from flask import g, request

MODULE_ENDPOINTS = {
    "customer_workspace", "customer_order_tracking", "customer_order_tracking_details",
    "designer_workspace", "designer_order_tracking", "designer_order_tracking_details",
    "customer_dashboard", "freelancer_dashboard", "customer_home", "designer_home", "dashboard",
}


def register_workspace_theme(app):
    @app.before_request
    def select_workspace_theme():
        g.workspace_mode = request.endpoint in MODULE_ENDPOINTS and request.args.get("workspace") == "1"

    @app.url_defaults
    def keep_workspace_theme(endpoint, values):
        if getattr(g, "workspace_mode", False) and endpoint in MODULE_ENDPOINTS:
            values.setdefault("workspace", "1")

    @app.context_processor
    def workspace_theme_context():
        def module_url(value):
            parts = urlsplit(value)
            if parts.scheme or parts.netloc or not parts.path.startswith(("/customer", "/designer")):
                return value
            args = dict(parse_qsl(parts.query, keep_blank_values=True))
            args["workspace"] = "1"
            return urlunsplit(("", "", parts.path, urlencode(args), parts.fragment))
        return dict(workspace_mode=getattr(g, "workspace_mode", False), workspace_module_url=module_url)
