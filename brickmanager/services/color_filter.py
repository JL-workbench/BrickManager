def selected_color_ids(settings):
    return {int(color_id) for color_id in settings.get("selected_color_ids", [])}


def is_filter_active(settings):
    return bool(settings.get("color_filter_enabled", False))


def color_is_visible(settings, color_id):
    return not is_filter_active(settings) or int(color_id) in selected_color_ids(
        settings
    )


def sort_filtered_parts(settings):
    return bool(settings.get("sort_filtered_parts", False))
