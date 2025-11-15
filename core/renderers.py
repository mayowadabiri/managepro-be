from djangorestframework_camel_case.render import CamelCaseJSONRenderer


class CustomJSONRenderer(CamelCaseJSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response", None)

        # If it's already wrapped, don’t wrap again
        if isinstance(data, dict) and "success" in data:
            return super().render(data, accepted_media_type, renderer_context)

        # Handle error codes separately
        if response is not None and response.status_code >= 400:
            formatted = {
                "success": False,
                "message": data.get(
                    "message", "Error processing your request, Please try again"
                ),
                "errors": data.get("errors", None),
                "code": data.get("code", None),
            }
        else:
            formatted = {
                "success": True,
                "message": "Success",
                "data": data,
            }

        return super().render(formatted, accepted_media_type, renderer_context)
